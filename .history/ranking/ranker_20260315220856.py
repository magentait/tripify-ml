# ranking/ranker.py
"""
Production-ready hotel ranking service.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import lightgbm as lgb

from .features import HotelFeatureExtractor

logger = logging.getLogger(__name__)


class HotelRanker:
    """Ranks hotels based on a trained LambdaMART model."""

    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model: Optional[lgb.Booster] = None
        self.feature_names: list[str] = []

    def load_model(self, name: str = "hotel_ranker_v1") -> None:
        model_path = self.model_dir / f"{name}.lgb"
        meta_path = self.model_dir / f"{name}_meta.json"

        meta = json.loads(meta_path.read_text())
        self.feature_names = meta["feature_names"]
        self.model = lgb.Booster(model_file=str(model_path))

        logger.info(
            f"Loaded model with {self.model.num_trees()} trees, "
            f"{len(self.feature_names)} features"
        )

    def rank(
        self,
        api_response: dict,
        user_context: Optional[dict] = None,
        top_k: Optional[int] = None,
        business_rules: Optional[dict] = None,
    ) -> list[dict]:
        t0 = time.perf_counter()
        hotels = api_response.get("hotels", [])

        if not hotels:
            return []

        business_rules = business_rules or {}

        hotels = self._pre_filter(hotels, business_rules)

        extractor = HotelFeatureExtractor(user_context=user_context)
        feature_dicts = extractor.extract_batch(hotels)

        df = pd.DataFrame(feature_dicts)
        for col in self.feature_names:
            if col not in df.columns:
                df[col] = 0.0

        X = df[self.feature_names].values.astype(np.float32)

        scores = self.model.predict(X)

        scores = self._apply_business_rules(
            scores, hotels, feature_dicts, business_rules
        )

        ranked_indices = np.argsort(-scores)

        result = []
        for rank_pos, idx in enumerate(ranked_indices):
            hotel = hotels[idx].copy()
            hotel["_rank_score"] = float(scores[idx])
            hotel["_rank_position"] = rank_pos + 1
            result.append(hotel)

        sponsored = set(business_rules.get("sponsored_hids", []))
        if sponsored:
            result = self._pin_sponsored(result, sponsored)

        if top_k:
            result = result[:top_k]

        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            f"Ranked {len(hotels)} hotels in {elapsed:.1f}ms "
            f"(top score: {result[0]['_rank_score']:.3f})"
        )

        return result

    def _pre_filter(self, hotels: list[dict], rules: dict) -> list[dict]:
        min_rating = rules.get("min_rating")
        if min_rating is not None:
            hotels = [
                h for h in hotels
                if (h.get("reviews") or {}).get("rating", 0) >= min_rating
            ]
        return hotels

    def _apply_business_rules(
        self,
        scores: np.ndarray,
        hotels: list[dict],
        features: list[dict],
        rules: dict,
    ) -> np.ndarray:
        scores = scores.copy()

        boost_cancel = rules.get("boost_cancellable", 0.0)
        if boost_cancel:
            for i, h in enumerate(hotels):
                terms = h.get("terms_placement") or {}
                if terms.get("cancelation"):
                    scores[i] += boost_cancel

        penalize_no_reviews = rules.get("penalize_no_reviews", 0.0)
        if penalize_no_reviews:
            for i, f in enumerate(features):
                if f.get("review_count", 0) == 0:
                    scores[i] -= penalize_no_reviews

        return scores

    def _pin_sponsored(
        self, result: list[dict], sponsored_hids: set
    ) -> list[dict]:
        sponsored = [h for h in result if h.get("hid") in sponsored_hids]
        non_sponsored = [
            h for h in result if h.get("hid") not in sponsored_hids
        ]
        merged = []
        s_idx, n_idx = 0, 0
        for pos in range(len(result)):
            if pos % 3 == 0 and s_idx < len(sponsored):
                merged.append(sponsored[s_idx])
                s_idx += 1
            elif n_idx < len(non_sponsored):
                merged.append(non_sponsored[n_idx])
                n_idx += 1
        merged.extend(sponsored[s_idx:])
        merged.extend(non_sponsored[n_idx:])
        return merged

    def rank_batch(
        self,
        api_responses: list[dict],
        user_contexts: list,
        **kwargs,
    ) -> list[list[dict]]:
        return [
            self.rank(resp, ctx, **kwargs)
            for resp, ctx in zip(api_responses, user_contexts)
        ]