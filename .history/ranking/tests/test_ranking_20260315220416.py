# tests/test_ranking.py

import pytest
import json
import numpy as np
import pandas as pd

from ranking.features import HotelFeatureExtractor
from ranking.data_generator import SyntheticHotelGenerator
from ranking.train import HotelRankingTrainer
from ranking.ranker import HotelRanker


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def sample_hotel() -> dict:
    return {
        "hid": 7467355,
        "title": "Florida Radison 5*",
        "link": "https://...",
        "description": "Contemporary hotel with a restaurant, business center & fitness room.",
        "address": "Address0, Address1",
        "gps_coordinates": {"latitude": 40.7089767, "longitude": -74.0091231},
        "city": "New York",
        "country": "US",
        "currency": "USD",
        "price": 176,
        "nearby_places": {
            "food": [{"title": "Pool Bar", "distance": 2, "unit": "km"}],
            "beaches": [{"title": "Ladies Club", "distance": 500, "unit": "m"}],
        },
        "hotel_class": 3,
        "reviews": {
            "total": 928,
            "rating": 3.7,
            "reviews_histogram": {"1": 120, "2": 63, "3": 143, "4": 266, "5": 336},
            "reviews_classes": {
                "cleanliness": 7.8, "service": 9.0,
                "price_quality": 9.5, "room": 10.0, "location": 8.3,
            },
            "comments": [
                {
                    "author": "Natalia", "country": "RU",
                    "vacation_type": "family", "rating": 9.0,
                    "good_part": "Very nice", "bad_part": None,
                    "common_text": None, "review_date": "2025-11-10",
                    "photos": [{"link": "https://..."}],
                }
            ],
            "total_comments": 300,
        },
        "terms_placement": {
            "check_in": {"after_time": "14:00", "before_time": "00:00", "timezone": "UTC"},
            "check_out": {"after_time": "00:00", "before_time": "12:00", "timezone": "UTC"},
            "cancelation": True,
            "refund_rule": {
                "refund_prepayment": True,
                "conditions": [
                    {"quantity_percent": 100, "condition": "If cancelation before 2 days"},
                    {"quantity_percent": 50, "condition": "If cancelation before 1 day"},
                ],
            },
            "smoking": False,
            "pet_friendly": False,
            "party_friendly": False,
            "age_restriction": "18+",
            "additional_info": "Some",
        },
        "payment_methods": {
            "cash_info": {"is_cash": True, "currency": ["AED", "USD", "RUB"]},
            "cards_info": {"is_card": True, "card_types": ["VISA", "JCB", "MASTERCARD"]},
        },
        "facilities": [
            {"type": "transfer", "is_free": False},
            {"type": "bath", "is_free": True},
        ],
    }


@pytest.fixture
def user_context() -> dict:
    return {
        "user_lat": 40.7128,
        "user_lng": -74.0060,
        "vacation_type": "family",
        "budget_tier": "mid",
        "preferred_currency": "USD",
    }


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    gen = SyntheticHotelGenerator()
    return gen.generate_dataset(n_queries=20, hotels_per_query=(10, 20), seed=123)


# ------------------------------------------------------------------ #
#  Feature extraction tests                                            #
# ------------------------------------------------------------------ #

class TestFeatureExtraction:

    def test_extract_returns_dict(self, sample_hotel, user_context):
        extractor = HotelFeatureExtractor(user_context=user_context)
        features = extractor.extract(sample_hotel)
        assert isinstance(features, dict)
        assert len(features) > 50  # We expect ~80+ features

    def test_price_features(self, sample_hotel, user_context):
        extractor = HotelFeatureExtractor(user_context=user_context)
        features = extractor.extract(sample_hotel)
        assert features["price"] == 176.0
        assert features["log_price"] > 0
        assert features["price_bucket"] == 2  # 150 < 176 <= 300

    def test_review_features(self, sample_hotel, user_context):
        extractor = HotelFeatureExtractor(user_context=user_context)
        features = extractor.extract(sample_hotel)
        assert features["review_count"] == 928.0
        assert features["review_rating"] == 3.7
        assert 0 < features["bayesian_rating"] < 5.0
        assert features["rc_mean"] > 0
        assert features["star_5_ratio"] > features["star_1_ratio"]

    def test_nearby_features(self, sample_hotel, user_context):
        extractor = HotelFeatureExtractor(user_context=user_context)
        features = extractor.extract(sample_hotel)
        assert features["nearby_food_count"] == 1.0
        assert features["nearby_food_min_dist_m"] == 2000.0  # 2 km
        assert features["nearby_beaches_min_dist_m"] == 500.0

    def test_facility_features(self, sample_hotel, user_context):
        extractor = HotelFeatureExtractor(user_context=user_context)
        features = extractor.extract(sample_hotel)
        assert features["total_facilities"] == 2.0
        assert features["fac_transfer"] == 1.0
        assert features["fac_bath"] == 1.0
        assert features["fac_pool"] == 0.0

    def test_distance_to_user(self, sample_hotel, user_context):
        extractor = HotelFeatureExtractor(user_context=user_context)
        features = extractor.extract(sample_hotel)
        # Hotel is very close to user (both in NYC area)
        assert features["dist_to_user_km"] < 5.0

    def test_user_currency_match(self, sample_hotel, user_context):
        extractor = HotelFeatureExtractor(user_context=user_context)
        features = extractor.extract(sample_hotel)
        assert features["accepts_user_currency"] == 1.0  # USD in cash currencies

    def test_no_user_context(self, sample_hotel):
        extractor = HotelFeatureExtractor()
        features = extractor.extract(sample_hotel)
        assert features["dist_to_user_km"] == 0.0
        assert features["accepts_user_currency"] == 0.0

    def test_batch_extraction(self, sample_hotel, user_context):
        extractor = HotelFeatureExtractor(user_context=user_context)
        batch = extractor.extract_batch([sample_hotel, sample_hotel])
        assert len(batch) == 2
        assert batch[0] == batch[1]

    def test_missing_fields_handled_gracefully(self, user_context):
        minimal_hotel = {"hid": 1, "price": 100}
        extractor = HotelFeatureExtractor(user_context=user_context)
        features = extractor.extract(minimal_hotel)
        assert features["price"] == 100.0
        assert features["review_count"] == 0.0
        assert features["total_facilities"] == 0.0


# ------------------------------------------------------------------ #
#  Data generation tests                                               #
# ------------------------------------------------------------------ #

class TestDataGeneration:

    def test_generates_correct_shape(self, synthetic_df):
        assert len(synthetic_df) > 100
        assert "qid" in synthetic_df.columns
        assert "relevance" in synthetic_df.columns

    def test_relevance_distribution(self, synthetic_df):
        # Should have all 5 relevance levels
        assert set(synthetic_df["relevance"].unique()).issubset({0, 1, 2, 3, 4})
        # At least 3 different levels
        assert len(synthetic_df["relevance"].unique()) >= 3

    def test_multiple_queries(self, synthetic_df):
        assert synthetic_df["qid"].nunique() == 20

    def test_deterministic_with_seed(self):
        gen = SyntheticHotelGenerator()
        df1 = gen.generate_dataset(n_queries=5, seed=99)
        df2 = gen.generate_dataset(n_queries=5, seed=99)
        pd.testing.assert_frame_equal(df1, df2)


# ------------------------------------------------------------------ #
#  Training tests                                                      #
# ------------------------------------------------------------------ #

class TestTraining:

    def test_model_trains_without_error(self, synthetic_df):
        trainer = HotelRankingTrainer(
            params={
                **HotelRankingTrainer.DEFAULT_PARAMS,
                "n_estimators": 50,
                "num_leaves": 15,
            }
        )
        unique_qids = synthetic_df["qid"].unique()
        split = int(len(unique_qids) * 0.8)
        train_df = synthetic_df[synthetic_df["qid"].isin(unique_qids[:split])]
        val_df = synthetic_df[synthetic_df["qid"].isin(unique_qids[split:])]

        model = trainer.train(train_df, val_df, early_stopping_rounds=10)
        assert model is not None
        assert trainer.model.best_iteration_ > 0

    def test_model_predicts_scores(self, synthetic_df):
        trainer = HotelRankingTrainer(
            params={
                **HotelRankingTrainer.DEFAULT_PARAMS,
                "n_estimators": 30,
                "num_leaves": 10,
            }
        )
        trainer.train(synthetic_df)
        X, y, groups = trainer.prepare_features(synthetic_df)
        scores = trainer.model.predict(X)
        assert len(scores) == len(X)
        assert not np.any(np.isnan(scores))

    def test_save_and_load(self, synthetic_df, tmp_path):
        trainer = HotelRankingTrainer(
            model_dir=str(tmp_path),
            params={
                **HotelRankingTrainer.DEFAULT_PARAMS,
                "n_estimators": 20,
                "num_leaves": 10,
            },
        )
        trainer.train(synthetic_df)
        X, _, _ = trainer.prepare_features(synthetic_df)
        scores_before = trainer.model.predict(X)

        trainer.save("test_model")

        # Load into new trainer
        trainer2 = HotelRankingTrainer(model_dir=str(tmp_path))
        trainer2.load("test_model")
        X2, _, _ = trainer2.prepare_features(synthetic_df)
        scores_after = trainer2.model.predict(X2)

        np.testing.assert_array_almost_equal(scores_before, scores_after, decimal=5)


# ------------------------------------------------------------------ #
#  Integration test                                                    #
# ------------------------------------------------------------------ #

class TestIntegration:

    def test_end_to_end_ranking(self, sample_hotel, user_context, tmp_path):
        """Full pipeline: generate -> train -> rank."""
        # Generate data
        gen = SyntheticHotelGenerator()
        df = gen.generate_dataset(n_queries=30, seed=42)

        # Train
        trainer = HotelRankingTrainer(
            model_dir=str(tmp_path),
            params={
                **HotelRankingTrainer.DEFAULT_PARAMS,
                "n_estimators": 50,
                "num_leaves": 15,
            },
        )
        trainer.train(df)
        trainer.save("test_e2e")

        # Rank
        from ranker import HotelRanker
        ranker = HotelRanker(model_dir=str(tmp_path))
        ranker.load_model("test_e2e")

        api_response = {
            "hotels": [sample_hotel, {**sample_hotel, "hid": 2, "price": 500}],
            "provider_id": 1,
            "provider_name": "Test",
            "total_hotels": 2,
        }

        ranked = ranker.rank(api_response, user_context)
        assert len(ranked) == 2
        assert "_rank_score" in ranked[0]
        assert "_rank_position" in ranked[0]
        # The cheaper/better-rated one should rank higher (generally)
        assert ranked[0]["_rank_score"] >= ranked[1]["_rank_score"]