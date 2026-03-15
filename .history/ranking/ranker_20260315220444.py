# train.py
"""
Trains a LambdaMART ranking model using LightGBM.
Supports both synthetic cold-start training and fine-tuning on real data.
"""

import os
import json
import pickle
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import GroupKFold

from features import HotelFeatureExtractor
from .data_generator import SyntheticHotelGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Columns that are NOT features
META_COLS = {"qid", "relevance", "hid"}


class HotelRankingTrainer:
    """
    Trains and evaluates a hotel ranking model.
    
    Architecture: LambdaMART (LightGBM ranker) — state-of-the-art for
    tabular LTR with graded relevance labels.
    """

    DEFAULT_PARAMS = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "eval_at": [5, 10, 20],
        "boosting_type": "gbdt",
        "num_leaves": 127,
        "max_depth": 8,
        "learning_rate": 0.05,
        "n_estimators": 1500,
        "min_child_samples": 20,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
        "lambdarank_truncation_level": 20,
    }

    def __init__(
        self,
        model_dir: str = "models",
        params: dict | None = None,
    ):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self.model: lgb.LGBMRanker | None = None
        self.feature_names: list[str] = []

    # ------------------------------------------------------------------ #
    #  Data preparation                                                    #
    # ------------------------------------------------------------------ #

    def prepare_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, np.ndarray]:
        """
        Splits DataFrame into X (features), y (relevance), groups.
        """
        feature_cols = [c for c in df.columns if c not in META_COLS]
        X = df[feature_cols].copy()
        y = df["relevance"].astype(int)

        # Compute group sizes (number of hotels per query)
        groups = df.groupby("qid").size().values

        self.feature_names = feature_cols
        return X, y, groups

    # ------------------------------------------------------------------ #
    #  Training                                                            #
    # ------------------------------------------------------------------ #

    def train(
        self,
        df: pd.DataFrame,
        val_df: pd.DataFrame | None = None,
        early_stopping_rounds: int = 100,
    ) -> lgb.LGBMRanker:
        """
        Train the LambdaMART model.
        
        Args:
            df: training data with qid, relevance, and feature columns
            val_df: optional validation set
            early_stopping_rounds: patience for early stopping
        """
        X_train, y_train, groups_train = self.prepare_features(df)

        logger.info(
            f"Training set: {len(X_train)} samples, "
            f"{len(groups_train)} queries, "
            f"{len(self.feature_names)} features"
        )
        logger.info(f"Relevance distribution:\n{y_train.value_counts().sort_index()}")

        self.model = lgb.LGBMRanker(**self.params)

        fit_params = {
            "X": X_train,
            "y": y_train,
            "group": groups_train,
        }

        callbacks = [lgb.log_evaluation(period=100)]

        if val_df is not None:
            X_val, y_val, groups_val = self.prepare_features(val_df)
            fit_params["eval_set"] = [(X_val, y_val)]
            fit_params["eval_group"] = [groups_val]
            fit_params["eval_names"] = ["validation"]
            callbacks.append(
                lgb.early_stopping(stopping_rounds=early_stopping_rounds)
            )

        fit_params["callbacks"] = callbacks
        self.model.fit(**fit_params)

        logger.info(f"Best iteration: {self.model.best_iteration_}")

        return self.model

    def cross_validate(
        self,
        df: pd.DataFrame,
        n_splits: int = 5,
    ) -> dict[str, list[float]]:
        """
        Group K-Fold cross-validation.
        Returns NDCG@5/10/20 per fold.
        """
        X, y, _ = self.prepare_features(df)
        qids = df["qid"].values

        gkf = GroupKFold(n_splits=n_splits)
        results = {"ndcg@5": [], "ndcg@10": [], "ndcg@20": []}

        for fold, (train_idx, val_idx) in enumerate(
            gkf.split(X, y, groups=qids)
        ):
            logger.info(f"Fold {fold + 1}/{n_splits}")

            train_df = df.iloc[train_idx].copy()
            val_df = df.iloc[val_idx].copy()

            model = HotelRankingTrainer(params=self.params)
            model.train(train_df, val_df)

            # Evaluate
            X_val, y_val, groups_val = model.prepare_features(val_df)
            scores = model.model.predict(X_val)

            ndcg_scores = self._compute_ndcg_per_query(
                y_val.values, scores, groups_val
            )
            for k in [5, 10, 20]:
                results[f"ndcg@{k}"].append(ndcg_scores[k])

            logger.info(
                f"  NDCG@5={ndcg_scores[5]:.4f}, "
                f"NDCG@10={ndcg_scores[10]:.4f}, "
                f"NDCG@20={ndcg_scores[20]:.4f}"
            )

        for key in results:
            vals = results[key]
            logger.info(f"Mean {key}: {np.mean(vals):.4f} ± {np.std(vals):.4f}")

        return results

    # ------------------------------------------------------------------ #
    #  Evaluation helpers                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _dcg(relevances: np.ndarray, k: int) -> float:
        relevances = relevances[:k]
        gains = 2 ** relevances - 1
        discounts = np.log2(np.arange(len(relevances)) + 2)
        return float(np.sum(gains / discounts))

    def _ndcg(self, y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
        order = np.argsort(-y_score)
        y_sorted = y_true[order]
        dcg = self._dcg(y_sorted, k)
        ideal_order = np.argsort(-y_true)
        idcg = self._dcg(y_true[ideal_order], k)
        return dcg / idcg if idcg > 0 else 0.0

    def _compute_ndcg_per_query(
        self,
        y_true: np.ndarray,
        y_score: np.ndarray,
        groups: np.ndarray,
    ) -> dict[int, float]:
        results = {5: [], 10: [], 20: []}
        idx = 0
        for g in groups:
            g_true = y_true[idx: idx + g]
            g_score = y_score[idx: idx + g]
            for k in [5, 10, 20]:
                results[k].append(self._ndcg(g_true, g_score, k))
            idx += g
        return {k: float(np.mean(v)) for k, v in results.items()}

    # ------------------------------------------------------------------ #
    #  Persistence                                                         #
    # ------------------------------------------------------------------ #

    def save(self, name: str = "hotel_ranker_v1") -> Path:
        """Save model + feature names."""
        model_path = self.model_dir / f"{name}.lgb"
        meta_path = self.model_dir / f"{name}_meta.json"

        self.model.booster_.save_model(str(model_path))

        meta = {
            "feature_names": self.feature_names,
            "params": self.params,
            "best_iteration": self.model.best_iteration_,
        }
        meta_path.write_text(json.dumps(meta, indent=2))

        logger.info(f"Model saved to {model_path}")
        return model_path

    def load(self, name: str = "hotel_ranker_v1") -> None:
        """Load model + feature names."""
        model_path = self.model_dir / f"{name}.lgb"
        meta_path = self.model_dir / f"{name}_meta.json"

        meta = json.loads(meta_path.read_text())
        self.feature_names = meta["feature_names"]
        self.params = meta["params"]

        self.model = lgb.LGBMRanker(**self.params)
        self.model._Booster = lgb.Booster(model_file=str(model_path))
        self.model.fitted_ = True
        self.model._best_iteration = meta.get("best_iteration", -1)

        logger.info(f"Model loaded from {model_path}")


# ------------------------------------------------------------------ #
#  CLI entry point                                                     #
# ------------------------------------------------------------------ #

def main():
    """Full training pipeline."""
    logger.info("=" * 60)
    logger.info("HOTEL RANKING MODEL — TRAINING PIPELINE")
    logger.info("=" * 60)

    # 1) Generate synthetic data
    logger.info("Step 1: Generating synthetic training data...")
    gen = SyntheticHotelGenerator()
    df = gen.generate_dataset(n_queries=800, hotels_per_query=(15, 60), seed=42)
    logger.info(f"Generated {len(df)} samples across {df['qid'].nunique()} queries")

    # 2) Train/val split by query groups
    unique_qids = df["qid"].unique()
    np.random.seed(42)
    np.random.shuffle(unique_qids)
    split = int(len(unique_qids) * 0.8)
    train_qids = set(unique_qids[:split])
    val_qids = set(unique_qids[split:])

    train_df = df[df["qid"].isin(train_qids)].reset_index(drop=True)
    val_df = df[df["qid"].isin(val_qids)].reset_index(drop=True)

    logger.info(f"Train: {len(train_df)} samples, Val: {len(val_df)} samples")

    # 3) Train
    logger.info("Step 2: Training LambdaMART model...")
    trainer = HotelRankingTrainer()
    trainer.train(train_df, val_df, early_stopping_rounds=150)

    # 4) Feature importance
    logger.info("Step 3: Feature importance (top 20):")
    importance = pd.Series(
        trainer.model.feature_importances_,
        index=trainer.feature_names,
    ).sort_values(ascending=False)
    for feat, imp in importance.head(20).items():
        logger.info(f"  {feat:40s} {imp:6d}")

    # 5) Save
    trainer.save("hotel_ranker_v1")

    # 6) Cross-validation
    logger.info("Step 4: Cross-validation...")
    trainer.cross_validate(df, n_splits=5)

    logger.info("Done!")


if __name__ == "__main__":
    main()