# features.py
"""
Feature extraction from hotel API contract.
Converts raw hotel JSON into a flat feature vector for the ranking model.
"""

import math
import numpy as np
from datetime import datetime
from typing import Any


class HotelFeatureExtractor:
    """
    Extracts ML features from the hotel API contract.
    
    Produces a dict of named features that can be fed into
    pandas DataFrame -> model pipeline.
    """

    # Known facility types for one-hot encoding
    KNOWN_FACILITIES = [
        "transfer", "bath", "pool", "spa", "gym", "wifi",
        "parking", "restaurant", "bar", "laundry", "concierge",
        "room_service", "airport_shuttle", "kids_club",
    ]

    REVIEW_CLASSES = [
        "cleanliness", "service", "price_quality", "room", "location"
    ]

    def __init__(self, user_context: dict | None = None):
        """
        Args:
            user_context: optional dict with user-specific signals:
                - user_lat, user_lng: user's search center
                - vacation_type: "family" | "business" | "solo" | "couple"
                - budget_tier: "low" | "mid" | "high"
                - check_in_date: str ISO
                - check_out_date: str ISO
                - preferred_currency: str
        """
        self.user_context = user_context or {}

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def extract(self, hotel: dict) -> dict[str, float]:
        """Main entry point: hotel JSON -> flat feature dict."""
        f: dict[str, float] = {}

        self._price_features(hotel, f)
        self._review_features(hotel, f)
        self._class_features(hotel, f)
        self._location_features(hotel, f)
        self._nearby_features(hotel, f)
        self._facility_features(hotel, f)
        self._terms_features(hotel, f)
        self._payment_features(hotel, f)
        self._text_features(hotel, f)
        self._user_context_features(hotel, f)

        return f

    def extract_batch(self, hotels: list[dict]) -> list[dict[str, float]]:
        return [self.extract(h) for h in hotels]

    # ------------------------------------------------------------------ #
    #  Feature groups                                                      #
    # ------------------------------------------------------------------ #

    def _price_features(self, h: dict, f: dict) -> None:
        price = h.get("price", 0) or 0
        f["price"] = float(price)
        f["log_price"] = math.log1p(price)
        # price bucket (0-4)
        if price <= 50:
            f["price_bucket"] = 0
        elif price <= 150:
            f["price_bucket"] = 1
        elif price <= 300:
            f["price_bucket"] = 2
        elif price <= 600:
            f["price_bucket"] = 3
        else:
            f["price_bucket"] = 4

    def _review_features(self, h: dict, f: dict) -> None:
        reviews = h.get("reviews") or {}
        total = reviews.get("total", 0) or 0
        rating = reviews.get("rating", 0.0) or 0.0

        f["review_count"] = float(total)
        f["log_review_count"] = math.log1p(total)
        f["review_rating"] = float(rating)

        # Bayesian average (shrink towards global mean 3.5, weight=30)
        C, m = 30.0, 3.5
        f["bayesian_rating"] = (C * m + total * rating) / (C + total)

        # Histogram-based features
        hist = reviews.get("reviews_histogram") or {}
        total_hist = sum(hist.values()) if hist else 1
        for star in range(1, 6):
            cnt = hist.get(str(star), 0)
            f[f"star_{star}_ratio"] = cnt / max(total_hist, 1)

        # Polarisation: ratio of (1+2) vs (4+5)
        neg = hist.get("1", 0) + hist.get("2", 0)
        pos = hist.get("4", 0) + hist.get("5", 0)
        f["review_polarisation"] = (pos - neg) / max(total_hist, 1)

        # Sub-ratings
        classes = reviews.get("reviews_classes") or {}
        for rc in self.REVIEW_CLASSES:
            f[f"rc_{rc}"] = float(classes.get(rc, 0.0))

        # Average of sub-ratings
        vals = [float(v) for v in classes.values()] if classes else [0.0]
        f["rc_mean"] = float(np.mean(vals))
        f["rc_std"] = float(np.std(vals))
        f["rc_min"] = float(np.min(vals))

        # Comments count & freshness
        total_comments = reviews.get("total_comments", 0) or 0
        f["total_comments"] = float(total_comments)

        comments = reviews.get("comments") or []
        if comments:
            dates = []
            sentiments_good = 0
            sentiments_bad = 0
            for c in comments:
                rd = c.get("review_date")
                if rd:
                    try:
                        dates.append(datetime.fromisoformat(rd))
                    except ValueError:
                        pass
                if c.get("good_part"):
                    sentiments_good += 1
                if c.get("bad_part"):
                    sentiments_bad += 1

            if dates:
                newest = max(dates)
                days_since = (datetime.now() - newest).days
                f["days_since_latest_review"] = float(max(days_since, 0))
            else:
                f["days_since_latest_review"] = 9999.0

            f["comment_good_ratio"] = sentiments_good / len(comments)
            f["comment_bad_ratio"] = sentiments_bad / len(comments)
            f["has_photos_in_reviews"] = float(
                any(c.get("photos") for c in comments)
            )
        else:
            f["days_since_latest_review"] = 9999.0
            f["comment_good_ratio"] = 0.0
            f["comment_bad_ratio"] = 0.0
            f["has_photos_in_reviews"] = 0.0

    def _class_features(self, h: dict, f: dict) -> None:
        hc = h.get("hotel_class", 0) or 0
        f["hotel_class"] = float(hc)
        for c in range(1, 6):
            f[f"hotel_class_{c}"] = float(hc == c)

    def _location_features(self, h: dict, f: dict) -> None:
        gps = h.get("gps_coordinates") or {}
        lat = gps.get("latitude", 0.0)
        lng = gps.get("longitude", 0.0)
        f["latitude"] = float(lat)
        f["longitude"] = float(lng)

        # Distance from user search center (if available)
        ulat = self.user_context.get("user_lat")
        ulng = self.user_context.get("user_lng")
        if ulat is not None and ulng is not None:
            f["dist_to_user_km"] = self._haversine(lat, lng, ulat, ulng)
            f["log_dist_to_user"] = math.log1p(f["dist_to_user_km"])
        else:
            f["dist_to_user_km"] = 0.0
            f["log_dist_to_user"] = 0.0

    def _nearby_features(self, h: dict, f: dict) -> None:
        nearby = h.get("nearby_places") or {}

        for category in ["food", "beaches", "attractions", "transport"]:
            places = nearby.get(category) or []
            f[f"nearby_{category}_count"] = float(len(places))
            if places:
                dists = [self._normalize_distance(p) for p in places]
                f[f"nearby_{category}_min_dist_m"] = float(min(dists))
                f[f"nearby_{category}_avg_dist_m"] = float(np.mean(dists))
            else:
                f[f"nearby_{category}_min_dist_m"] = 99999.0
                f[f"nearby_{category}_avg_dist_m"] = 99999.0

    def _facility_features(self, h: dict, f: dict) -> None:
        facilities = h.get("facilities") or []
        fac_set = {}
        free_count = 0
        for fac in facilities:
            ftype = fac.get("type", "").lower()
            fac_set[ftype] = True
            if fac.get("is_free"):
                free_count += 1

        f["total_facilities"] = float(len(facilities))
        f["free_facilities"] = float(free_count)
        f["free_facility_ratio"] = (
            free_count / len(facilities) if facilities else 0.0
        )

        for ft in self.KNOWN_FACILITIES:
            f[f"fac_{ft}"] = float(ft in fac_set)

    def _terms_features(self, h: dict, f: dict) -> None:
        terms = h.get("terms_placement") or {}

        f["has_cancellation"] = float(bool(terms.get("cancelation")))
        f["is_smoking"] = float(bool(terms.get("smoking")))
        f["is_pet_friendly"] = float(bool(terms.get("pet_friendly")))
        f["is_party_friendly"] = float(bool(terms.get("party_friendly")))

        # Refund quality score
        refund = terms.get("refund_rule") or {}
        f["has_refund"] = float(bool(refund.get("refund_prepayment")))
        conditions = refund.get("conditions") or []
        if conditions:
            max_refund = max(c.get("quantity_percent", 0) for c in conditions)
            f["max_refund_percent"] = float(max_refund)
            f["refund_conditions_count"] = float(len(conditions))
        else:
            f["max_refund_percent"] = 0.0
            f["refund_conditions_count"] = 0.0

        # Check-in flexibility (hours window)
        ci = terms.get("check_in") or {}
        co = terms.get("check_out") or {}
        f["checkin_after_hour"] = self._parse_hour(ci.get("after_time", "14:00"))
        f["checkout_before_hour"] = self._parse_hour(co.get("before_time", "12:00"))
        f["stay_window_hours"] = max(
            0, (24 - f["checkin_after_hour"]) + f["checkout_before_hour"]
        )

    def _payment_features(self, hotel: dict, f: dict) -> None:
        """Payment-related features."""
        pm = hotel.get("payment_methods", [])

        # payment_methods может быть списком строк ["USD", "EUR"]
        # или словарём с деталями
        if isinstance(pm, list):
            accepted_currencies = set()
            for item in pm:
                if isinstance(item, str):
                    accepted_currencies.add(item.upper())
                elif isinstance(item, dict):
                    currency = item.get("currency", "")
                    if currency:
                        accepted_currencies.add(currency.upper())
            
            f["payment_options_count"] = len(pm)
            f["accepts_user_currency"] = 0
            
            if self.user_context:
                user_curr = self.user_context.get("preferred_currency", "").upper()
                if user_curr and user_curr in accepted_currencies:
                    f["accepts_user_currency"] = 1
        elif isinstance(pm, dict):
            cash = pm.get("cash_info") or {}
            cards = pm.get("cards_info") or {}
            f["payment_options_count"] = len(cash) + len(cards)
            f["accepts_user_currency"] = 0
            
            if self.user_context:
                user_curr = self.user_context.get("preferred_currency", "").upper()
                all_currencies = set()
                for c in list(cash.values()) + list(cards.values()):
                    if isinstance(c, dict):
                        cur = c.get("currency", "")
                        if cur:
                            all_currencies.add(cur.upper())
                if user_curr and user_curr in all_currencies:
                    f["accepts_user_currency"] = 1
        else:
            f["payment_options_count"] = 0
            f["accepts_user_currency"] = 0
        
        # Fallback: проверяем поле currency на верхнем уровне
        if f["accepts_user_currency"] == 0 and self.user_context:
            user_curr = self.user_context.get("preferred_currency", "").upper()
            hotel_curr = hotel.get("currency", "").upper()
            if user_curr and hotel_curr == user_curr:
                f["accepts_user_currency"] = 1

    def _text_features(self, h: dict, f: dict) -> None:
        desc = h.get("description") or ""
        f["description_length"] = float(len(desc))
        f["has_description"] = float(len(desc) > 0)
        title = h.get("title") or ""
        # Star mention in title (e.g. "5*")
        f["title_mentions_star"] = float("*" in title)

    def _user_context_features(self, h: dict, f: dict) -> None:
        """Cross features between user context and hotel."""
        vtype = self.user_context.get("vacation_type", "unknown")
        f["ctx_is_family"] = float(vtype == "family")
        f["ctx_is_business"] = float(vtype == "business")
        f["ctx_is_solo"] = float(vtype == "solo")
        f["ctx_is_couple"] = float(vtype == "couple")

        # Family travellers value pet/kid-friendliness
        f["family_x_pet"] = f.get("is_pet_friendly", 0) * f.get("ctx_is_family", 0)

        budget = self.user_context.get("budget_tier", "mid")
        f["ctx_budget_low"] = float(budget == "low")
        f["ctx_budget_mid"] = float(budget == "mid")
        f["ctx_budget_high"] = float(budget == "high")

        # Price match: high budget * high price should not be penalised
        f["budget_price_match"] = 0.0
        pb = f.get("price_bucket", 2)
        if budget == "low" and pb <= 1:
            f["budget_price_match"] = 1.0
        elif budget == "mid" and 1 <= pb <= 3:
            f["budget_price_match"] = 1.0
        elif budget == "high" and pb >= 3:
            f["budget_price_match"] = 1.0

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _normalize_distance(place: dict) -> float:
        """Convert any distance to meters."""
        d = place.get("distance", 0) or 0
        unit = (place.get("unit") or "m").lower()
        if unit == "km":
            return d * 1000
        elif unit == "mi":
            return d * 1609.34
        return float(d)

    @staticmethod
    def _parse_hour(t: str) -> float:
        try:
            parts = t.split(":")
            return float(parts[0]) + float(parts[1]) / 60.0
        except (ValueError, IndexError):
            return 12.0