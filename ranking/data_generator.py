# data_generator.py
"""
Generates synthetic training data for the hotel ranking model.

In production you'd replace this with real click-through / booking data.
The target is a relevance label 0-4 (graded relevance for LambdaRank).
"""

import random
import math
import uuid
import numpy as np
import pandas as pd
from typing import Any
from .features import HotelFeatureExtractor


class SyntheticHotelGenerator:
    """
    Generates fake hotel JSONs + assigns ground-truth relevance labels
    based on a known scoring function (simulating user preferences).
    """

    COUNTRIES = ["US", "TR", "AE", "TH", "ES", "IT", "FR", "GR", "MX", "JP"]
    CURRENCIES = {
        "US": "USD", "TR": "TRY", "AE": "AED", "TH": "THB",
        "ES": "EUR", "IT": "EUR", "FR": "EUR", "GR": "EUR",
        "MX": "MXN", "JP": "JPY",
    }
    VACATION_TYPES = ["family", "business", "solo", "couple"]
    BUDGET_TIERS = ["low", "mid", "high"]
    FACILITY_POOL = [
        "transfer", "bath", "pool", "spa", "gym", "wifi",
        "parking", "restaurant", "bar", "laundry", "concierge",
        "room_service", "airport_shuttle", "kids_club",
    ]

    def generate_dataset(
        self,
        n_queries: int = 500,
        hotels_per_query: tuple[int, int] = (10, 50),
        seed: int = 42,
    ) -> pd.DataFrame:
        """
        Returns a DataFrame with columns:
          - qid: query group id
          - all feature columns from HotelFeatureExtractor
          - relevance: int 0-4
        """
        rng = random.Random(seed)
        np_rng = np.random.RandomState(seed)
        rows = []

        for qid in range(n_queries):
            # Random user context
            user_ctx = self._random_user_context(rng)
            extractor = HotelFeatureExtractor(user_context=user_ctx)

            n_hotels = rng.randint(*hotels_per_query)
            for _ in range(n_hotels):
                hotel = self._random_hotel(rng, np_rng, user_ctx)
                features = extractor.extract(hotel)

                # Compute ground-truth relevance from oracle scoring
                relevance = self._oracle_relevance(
                    hotel, user_ctx, features, rng, np_rng
                )

                features["qid"] = qid
                features["relevance"] = relevance
                rows.append(features)

        df = pd.DataFrame(rows)
        return df

    # ------------------------------------------------------------------ #
    #  Hotel generation                                                    #
    # ------------------------------------------------------------------ #

    def _random_hotel(
        self, rng: random.Random, np_rng: np.random.RandomState,
        user_ctx: dict
    ) -> dict:
        country = rng.choice(self.COUNTRIES)
        hotel_class = rng.choices([1, 2, 3, 4, 5], weights=[5, 10, 30, 35, 20])[0]

        base_price = {1: 30, 2: 60, 3: 120, 4: 220, 5: 400}[hotel_class]
        price = max(10, int(base_price * np_rng.lognormal(0, 0.4)))

        rating_base = {1: 2.5, 2: 3.0, 3: 3.5, 4: 4.0, 5: 4.3}[hotel_class]
        rating = round(np.clip(np_rng.normal(rating_base, 0.5), 1.0, 5.0), 1)
        total_reviews = int(np.clip(np_rng.lognormal(5, 1.5), 0, 15000))

        # Generate histogram consistent with rating
        hist = self._generate_histogram(rating, total_reviews, np_rng)

        # Sub-ratings
        review_classes = {}
        for rc in ["cleanliness", "service", "price_quality", "room", "location"]:
            review_classes[rc] = round(
                float(np.clip(np_rng.normal(rating * 2, 1.0), 1.0, 10.0)), 1
            )

        # GPS near user or random
        ulat = user_ctx.get("user_lat", 40.0)
        ulng = user_ctx.get("user_lng", 30.0)
        lat = ulat + np_rng.normal(0, 0.2)
        lng = ulng + np_rng.normal(0, 0.2)

        # Nearby places
        nearby = {}
        for cat in ["food", "beaches", "attractions"]:
            n = rng.randint(0, 5)
            places = []
            for _ in range(n):
                places.append({
                    "title": f"{cat}_{uuid.uuid4().hex[:6]}",
                    "distance": rng.randint(50, 5000),
                    "unit": "m",
                })
            nearby[cat] = places

        # Facilities
        n_fac = rng.randint(1, len(self.FACILITY_POOL))
        facs = rng.sample(self.FACILITY_POOL, n_fac)
        facilities = [
            {"type": ft, "is_free": rng.random() < 0.4} for ft in facs
        ]

        # Cancellation
        has_cancel = rng.random() < 0.7
        has_refund = has_cancel and rng.random() < 0.6

        # Comments
        n_comments = min(rng.randint(0, 10), total_reviews)
        comments = []
        for _ in range(n_comments):
            comments.append({
                "author": f"User_{uuid.uuid4().hex[:4]}",
                "country": rng.choice(self.COUNTRIES),
                "vacation_type": rng.choice(self.VACATION_TYPES),
                "rating": round(np.clip(np_rng.normal(rating * 2, 1.5), 1, 10), 1),
                "good_part": "Good" if rng.random() < 0.7 else None,
                "bad_part": "Bad" if rng.random() < 0.3 else None,
                "common_text": None,
                "review_date": f"2025-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}",
                "photos": [{"link": "https://..."}] if rng.random() < 0.3 else [],
            })

        hotel = {
            "hid": rng.randint(100000, 9999999),
            "title": f"Hotel_{hotel_class}star_{uuid.uuid4().hex[:6]}",
            "link": "https://example.com",
            "description": "A " * rng.randint(5, 50),
            "address": "Address",
            "gps_coordinates": {"latitude": lat, "longitude": lng},
            "city": "City",
            "country": country,
            "currency": self.CURRENCIES.get(country, "USD"),
            "price": price,
            "nearby_places": nearby,
            "hotel_class": hotel_class,
            "reviews": {
                "total": total_reviews,
                "rating": rating,
                "reviews_histogram": hist,
                "reviews_classes": review_classes,
                "comments": comments,
                "total_comments": len(comments),
            },
            "terms_placement": {
                "check_in": {"after_time": f"{rng.randint(12,16)}:00", "before_time": "00:00", "timezone": "UTC"},
                "check_out": {"after_time": "00:00", "before_time": f"{rng.randint(10,14)}:00", "timezone": "UTC"},
                "cancelation": has_cancel,
                "refund_rule": {
                    "refund_prepayment": has_refund,
                    "conditions": [
                        {"quantity_percent": 100, "condition": "before 2 days"},
                        {"quantity_percent": 50, "condition": "before 1 day"},
                    ] if has_refund else [],
                },
                "smoking": rng.random() < 0.2,
                "pet_friendly": rng.random() < 0.3,
                "party_friendly": rng.random() < 0.15,
                "age_restriction": "18+",
                "additional_info": "",
            },
            "payment_methods": {
                "cash_info": {
                    "is_cash": rng.random() < 0.6,
                    "currency": rng.sample(["USD", "EUR", "RUB", "AED"], rng.randint(1, 3)),
                },
                "cards_info": {
                    "is_card": True,
                    "card_types": rng.sample(
                        ["VISA", "MASTERCARD", "AMEX", "JCB", "UNIONPAY"],
                        rng.randint(1, 4),
                    ),
                },
            },
            "facilities": facilities,
        }
        return hotel

    def _random_user_context(self, rng: random.Random) -> dict:
        return {
            "user_lat": rng.uniform(25, 55),
            "user_lng": rng.uniform(-10, 50),
            "vacation_type": rng.choice(self.VACATION_TYPES),
            "budget_tier": rng.choice(self.BUDGET_TIERS),
            "preferred_currency": rng.choice(["USD", "EUR", "RUB"]),
        }

    def _generate_histogram(
        self, rating: float, total: int, np_rng: np.random.RandomState
    ) -> dict[str, int]:
        """Generate review histogram roughly consistent with mean rating."""
        if total == 0:
            return {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        # Use Dirichlet centered around the rating
        alpha = np.array([
            max(0.1, 5 - abs(i + 1 - rating) * 2) for i in range(5)
        ])
        probs = np_rng.dirichlet(alpha * 3)
        counts = np_rng.multinomial(total, probs)
        return {str(i + 1): int(counts[i]) for i in range(5)}

    # ------------------------------------------------------------------ #
    #  Oracle relevance (simulated user preference)                        #
    # ------------------------------------------------------------------ #

    def _oracle_relevance(
        self,
        hotel: dict,
        user_ctx: dict,
        features: dict[str, float],
        rng: random.Random,
        np_rng: np.random.RandomState,
    ) -> int:
        """
        Compute a 0-4 relevance label using a known scoring function.
        Designed to produce a realistic bell-curve distribution:
        ~15% label 0, ~25% label 1, ~30% label 2, ~20% label 3, ~10% label 4
        """
        score = 0.0

        # --- Rating signal (main) ---
        bayesian = features.get("bayesian_rating", 3.0)
        score += (bayesian - 3.0) * 6.0  # centered around 3.0

        # --- Review volume (diminishing returns) ---
        score += min(features.get("log_review_count", 0) * 0.8, 4.0)

        # --- Sub-rating quality ---
        rc_mean = features.get("rc_mean", 5.0)
        score += (rc_mean - 6.0) * 0.8  # centered around 6.0

        # --- Price sensitivity by budget ---
        budget = user_ctx.get("budget_tier", "mid")
        price = features.get("price", 150)
        if budget == "low":
            score -= price * 0.04
            if price > 200:
                score -= 3.0
        elif budget == "mid":
            score -= price * 0.015
        else:
            score += min(price * 0.003, 2.0)
            if price < 80:
                score -= 2.0  # too cheap for luxury traveller

        # --- Budget match ---
        score += features.get("budget_price_match", 0) * 2.0

        # --- Facilities (moderate impact) ---
        score += min(features.get("total_facilities", 0) * 0.3, 3.0)
        score += features.get("free_facility_ratio", 0) * 1.5

        # --- Cancellation & refund ---
        score += features.get("has_cancellation", 0) * 1.5
        score += features.get("has_refund", 0) * 1.0

        # --- Location proximity (strong penalty for far) ---
        dist = features.get("dist_to_user_km", 0)
        score -= dist * 0.8

        # --- Vacation type interactions ---
        vtype = user_ctx.get("vacation_type", "solo")
        if vtype in ("family", "couple"):
            beach_dist = features.get("nearby_beaches_min_dist_m", 99999)
            if beach_dist < 500:
                score += 2.0
            elif beach_dist < 2000:
                score += 0.5
            else:
                score -= 1.0
        if vtype == "business":
            score += features.get("fac_wifi", 0) * 1.5
            score += features.get("fac_gym", 0) * 1.0

        # --- Hotel class (mild) ---
        score += (features.get("hotel_class", 3) - 3) * 0.8

        # --- Payment ---
        score += features.get("accepts_user_currency", 0) * 1.0

        # --- Polarisation penalty ---
        score += features.get("review_polarisation", 0) * 2.0

        # --- Noise (important for realistic variance!) ---
        score += np_rng.normal(0, 4.0)

        # --- Map to 0-4 with percentile-based thresholds ---
        # Tuned to produce roughly: 15% / 25% / 30% / 20% / 10%
        if score < -4.0:
            return 0
        elif score < 0.0:
            return 1
        elif score < 4.0:
            return 2
        elif score < 8.0:
            return 3
        else:
            return 4