# finetune.py
"""
Fine-tuning the ranking model on real user interaction data.

Expected input: a CSV/Parquet with columns:
  - qid: search session ID
  - hid: hotel ID
  - clicked: 0/1
  - booked: 0/1
  - dwell_time_sec: time spent on hotel detail page
  - position_shown: position where hotel was displayed
  
We convert these signals into graded relevance labels
and retrain / fine-tune the model.
"""

import logging
import numpy as np
import pandas as pd

from .features import HotelFeatureExtractor
from .train import HotelRankingTrainer

logger = logging.getLogger(__name__)


class RealDataProcessor:
    """Converts raw interaction logs into training data for the ranker."""

    @staticmethod
    def compute_relevance(row: pd.Series) -> int:
        """
        Convert implicit feedback to graded relevance (0-4).
        
        Hierarchy:
          4 = booked
          3 = clicked + long dwell (>60s)
          2 = clicked + medium dwell (>15s)
          1 = clicked + short dwell
          0 = not clicked (with position bias correction)
        """
        if row.get("booked", 0):
            return 4
        if row.get("clicked", 0):
            dwell = row.get("dwell_time_sec", 0) or 0
            if dwell > 60:
                return 3
            elif dwell > 15:
                return 2
            else:
                return 1
        return 0

    @staticmethod
    def apply_position_bias_correction(
        df: pd.DataFrame, 
        examination_probs: dict[int, float] | None = None,
    ) -> pd.DataFrame:
        """
        Apply inverse propensity weighting for position bias.
        Hotels shown at lower positions had less chance of being seen.
        """
        if examination_probs is None:
            # Default examination probability by position (1-indexed)
            # Based on eye-tracking studies: P(examine) ≈ 1/log2(pos+1)
            examination_probs = {
                i: 1.0 / np.log2(i + 1) for i in range(1, 101)
            }

        df = df.copy()
        df["exam_prob"] = df["position_shown"].map(
            lambda p: examination_probs.get(int(p), 0.1)
        )
        df["ipw_weight"] = 1.0 / df["exam_prob"].clip(lower=0.05)
        # Normalise weights within each query group
        df["ipw_weight"] = df.groupby("qid")["ipw_weight"].transform(
            lambda x: x / x.sum() * len(x)
        )
        return df


def finetune_on_real_data(
    interaction_log_path: str,
    hotel_features_path: str,
    base_model_name: str = "hotel_ranker_v1",
    output_model_name: str = "hotel_ranker_v2_finetuned",
):
    """
    Full fine-tuning pipeline.
    
    Args:
        interaction_log_path: path to interaction CSV
        hotel_features_path: path to precomputed hotel features (parquet)
        base_model_name: name of the base model to load initial weights
        output_model_name: name for the fine-tuned model
    """
    logger.info("Loading interaction data...")
    interactions = pd.read_csv(interaction_log_path)

    logger.info("Computing relevance labels...")
    processor = RealDataProcessor()
    interactions["relevance"] = interactions.apply(
        processor.compute_relevance, axis=1
    )

    # Position bias correction
    interactions = processor.apply_position_bias_correction(interactions)

    logger.info("Loading hotel features...")
    hotel_features = pd.read_parquet(hotel_features_path)

    # Merge
    df = interactions.merge(hotel_features, on="hid", how="inner")
    logger.info(f"Training data: {len(df)} samples, {df['qid'].nunique()} queries")
    logger.info(f"Relevance distribution:\n{df['relevance'].value_counts().sort_index()}")

    # Train with warm start
    # LightGBM supports init_model for fine-tuning
    trainer = HotelRankingTrainer(
        params={
            **HotelRankingTrainer.DEFAULT_PARAMS,
            "learning_rate": 0.01,  # Lower LR for fine-tuning
            "n_estimators": 500,    # Fewer iterations
        }
    )

    # Split
    unique_qids = df["qid"].unique()
    np.random.seed(42)
    np.random.shuffle(unique_qids)
    split = int(len(unique_qids) * 0.85)
    train_qids = set(unique_qids[:split])
    val_qids = set(unique_qids[split:])

    train_df = df[df["qid"].isin(train_qids)].reset_index(drop=True)
    val_df = df[df["qid"].isin(val_qids)].reset_index(drop=True)

    # Load base model as init_model
    base_model_path = trainer.model_dir / f"{base_model_name}.lgb"

    trainer.train(train_df, val_df, early_stopping_rounds=50)
    # NOTE: For true warm-start, pass init_model to lgb.train():
    # This requires using the low-level API. Simplified here.

    trainer.save(output_model_name)
    logger.info(f"Fine-tuned model saved as {output_model_name}")