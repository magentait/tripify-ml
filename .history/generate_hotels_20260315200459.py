import json
import random
import uuid
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

# ─────────────────────────── справочники ───────────────────────────

COUNTRIES = [
    ("US", "USD"), ("GB", "GBP"), ("DE", "EUR"), ("FR", "EUR"),
    ("IT", "EUR"), ("ES", "EUR"), ("RU", "RUB"), ("AE", "AED"),
    ("TR", "TRY"), ("TH", "THB"), ("JP", "JPY"), ("CN", "CNY"),
    ("BR", "BRL"), ("IN", "INR"), ("AU", "AUD"), ("MX", "MXN"),
    ("EG", "EGP"), ("GR", "EUR"), ("PT", "EUR"), ("KR", "KRW"),
]

HOTEL_BRANDS = [
    "Radison", "Hilton", "Marriott", "Hyatt", "Sheraton",
    "Holiday Inn", "Best Western", "Ritz-Carlton", "Four Seasons",
    "InterContinental", "Novotel", "Accor", "Wyndham", "Ibis",
    "Kempinski", "Mandarin Oriental", "Fairmont", "Crowne Plaza",
    "Sofitel", "Park Hyatt",
]

STAR_LABELS = ["3*", "4*", "5*", "4* Superior", "5* Luxury"]

FOOD_PLACES = [
    "Pool Bar", "Lobby Lounge", "Sushi Corner", "Italian Trattoria",
    "Rooftop Restaurant", "Beach Café", "BBQ Terrace", "Tapas Bar",
    "Steakhouse", "Dim Sum Palace", "French Bistro", "Burger Joint",
]

BEACH_PLACES = [
    "Ladies Club", "Sunset Beach", "Coral Bay", "Palm Shore",
    "White Sand Beach", "Blue Lagoon", "Crystal Cove", "Golden Coast",
]

FACILITY_TYPES = [
    "transfer", "bath", "spa", "gym", "pool", "wifi", "parking",
    "restaurant", "bar", "laundry", "concierge", "room_service",
    "sauna", "kids_club", "business_center", "airport_shuttle",
]

VACATION_TYPES = ["family", "solo", "couple", "business", "friends", "group"]

CARD_TYPES = ["VISA", "MASTERCARD", "AMEX", "JSB", "UnionPay", "Mir"]

CURRENCIES_CASH = ["AED", "USD", "RUB", "EUR", "GBP", "TRY", "THB", "CNY"]

TIMEZONES = [
    "UTC", "Europe/London", "Europe/Paris", "Europe/Berlin",
    "Europe/Moscow", "America/New_York", "America/Chicago",
    "Asia/Dubai", "Asia/Tokyo", "Asia/Bangkok", "Asia/Shanghai",
    "Australia/Sydney", "America/Sao_Paulo",
]

GOOD_COMMENTS = [
    "Very nice hotel!", "Amazing service and clean rooms.",
    "Perfect location.", "Staff was extremely friendly.",
    "Breakfast was delicious.", "Would definitely come back!",
    "Beautiful view from the balcony.", "Exceeded expectations.",
    "Great value for money.", "Room was spacious and modern.",
    "The pool area was fantastic.", "Loved the spa experience.",
    "Everything was spotless.", "Best hotel I've ever stayed at.",
    "Wonderful atmosphere and decor.",
]

BAD_COMMENTS = [
    None, None, None, None, None,  # часто нет жалоб
    "Noisy at night.", "Wi-Fi was slow.", "Room was a bit small.",
    "AC didn't work properly.", "Food could be better.",
    "Check-in took too long.", "Parking was expensive.",
    "Towels were not replaced daily.",
]

COMMON_TEXTS = [
    None, None, None,
    "Overall a pleasant stay.", "Nothing special to add.",
    "Recommended for short stays.", "Good for families with kids.",
]

AUTHOR_NAMES = [
    "Natalia", "John", "Ahmed", "Yuki", "Maria", "Chen", "Oliver",
    "Fatima", "Dmitry", "Sophia", "Hans", "Aisha", "Carlos", "Priya",
    "Liam", "Elena", "Mohammed", "Anna", "James", "Sara", "Pedro",
    "Olga", "Ali", "Mia", "Ivan", "Chloe", "Raj", "Emma", "Wei",
]

REVIEW_COUNTRIES = [
    "RU", "US", "GB", "DE", "FR", "AE", "TR", "IN",
    "CN", "JP", "BR", "AU", "KR", "EG", "IT", "ES",
]

PROVIDER_ID = 1
PROVIDER_NAME = "Островок!"


# ─────────────────────── генераторы ────────────────────────────────

def gen_hid() -> int:
    return random.randint(1_000_000, 9_999_999)


def gen_gps():
    return {
        "latitude": round(random.uniform(-60, 70), 7),
        "longitude": round(random.uniform(-180, 180), 7),
    }


def gen_nearby_places():
    food = [
        {
            "title": random.choice(FOOD_PLACES),
            "distance": random.choice([0.1, 0.2, 0.5, 1, 2, 3, 5]),
            "unit": "km",
        }
        for _ in range(random.randint(1, 4))
    ]
    beaches = [
        {
            "title": random.choice(BEACH_PLACES),
            "distance": random.choice([100, 200, 300, 500, 800, 1000, 1500]),
            "unit": "m",
        }
        for _ in range(random.randint(0, 3))
    ]
    return {"food": food, "beaches": beaches}


def gen_reviews_histogram(total: int) -> dict:
    """Распределяем total отзывов по 5 звёздам."""
    parts = [random.random() for _ in range(5)]
    s = sum(parts)
    counts = [int(total * p / s) for p in parts]
    counts[4] += total - sum(counts)  # остаток в «5»
    return {str(i + 1): counts[i] for i in range(5)}


def gen_reviews_classes() -> dict:
    return {
        "cleanliness": round(random.uniform(5.0, 10.0), 1),
        "service": round(random.uniform(5.0, 10.0), 1),
        "price_quality": round(random.uniform(5.0, 10.0), 1),
        "room": round(random.uniform(5.0, 10.0), 1),
        "location": round(random.uniform(5.0, 10.0), 1),
    }


def gen_comment():
    num_photos = random.randint(0, 5)
    photos = [
        {"link": f"https://cdn.example.com/photos/{uuid.uuid4().hex}.jpg"}
        for _ in range(num_photos)
    ]
    review_date = fake.date_between(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2026, 12, 31),
    )
    return {
        "author": random.choice(AUTHOR_NAMES),
        "country": random.choice(REVIEW_COUNTRIES),
        "vacation_type": random.choice(VACATION_TYPES),
        "rating": round(random.uniform(1.0, 10.0), 1),
        "good_part": random.choice(GOOD_COMMENTS),
        "bad_part": random.choice(BAD_COMMENTS),
        "common_text": random.choice(COMMON_TEXTS),
        "review_date": review_date.isoformat(),
        "photos": photos if photos else [],
    }


def gen_reviews():
    total = random.randint(10, 5000)
    total_comments = random.randint(5, min(total, 500))
    num_comments = random.randint(1, min(total_comments, 15))  # в выдаче до 15

    return {
        "total": total,
        "rating": round(random.uniform(2.0, 5.0), 1),
        "reviews_histogram": gen_reviews_histogram(total),
        "reviews_classes": gen_reviews_classes(),
        "comments": [gen_comment() for _ in range(num_comments)],
        "total_comments": total_comments,
    }


def gen_terms_placement():
    check_in_after = random.choice(["12:00", "13:00", "14:00", "15:00"])
    check_in_before = random.choice(["00:00", "23:00", "22:00"])
    check_out_after = "00:00"
    check_out_before = random.choice(["10:00", "11:00", "12:00"])
    cancelation = random.choice([True, False])

    conditions = []
    if cancelation:
        conditions.append({
            "quantity_percent": 100,
            "condition": "If cancelation before 2 days check in room",
        })
        if random.random() > 0.3:
            conditions.append({
                "quantity_percent": 50,
                "condition": "If cancelation before 1 days check in room",
            })

    return {
        "check_in": {
            "after_time": check_in_after,
            "before_time": check_in_before,
            "timezone": random.choice(TIMEZONES),
        },
        "check_out": {
            "after_time": check_out_after,
            "before_time": check_out_before,
            "timezone": random.choice(TIMEZONES),
        },
        "cancelation": cancelation,
        "refund_rule": {
            "refund_prepayment": cancelation,
            "conditions": conditions,
        },
        "smoking": random.choice([True, False]),
        "pet_friendly": random.choice([True, False]),
        "party_friendly": random.choice([True, False]),
        "age_restriction": random.choice(["18+", "21+", "16+", None]),
        "additional_info": fake.sentence() if random.random() > 0.5 else None,
    }


def gen_payment_methods():
    is_cash = random.choice([True, True, True, False])
    is_card = random.choice([True, True, True, False])
    return {
        "cash_info": {
            "is_cash": is_cash,
            "currency": random.sample(CURRENCIES_CASH, k=random.randint(1, 4))
            if is_cash
            else [],
        },
        "cards_info": {
            "is_card": is_card,
            "card_types": random.sample(CARD_TYPES, k=random.randint(1, 4))
            if is_card
            else [],
        },
    }


def gen_facilities():
    n = random.randint(2, 8)
    chosen = random.sample(FACILITY_TYPES, k=n)
    return [
        {"type": t, "is_free": random.choice([True, False])}
        for t in chosen
    ]


def gen_hotel():
    country_code, currency = random.choice(COUNTRIES)
    city = fake.city()
    stars = random.choice(STAR_LABELS)
    brand = random.choice(HOTEL_BRANDS)
    title = f"{city} {brand} {stars}"
    hid = gen_hid()
    price = random.randint(30, 1500)
    hotel_class = random.randint(1, 5)

    return {
        "hid": hid,
        "title": title,
        "link": f"https://example.com/hotels/{hid}",
        "description": fake.sentence(nb_words=12),
        "address": f"{fake.street_address()}, {fake.secondary_address()}",
        "gps_coordinates": gen_gps(),
        "city": city,
        "country": country_code,
        "currency": currency,
        "price": price,
        "nearby_places": gen_nearby_places(),
        "hotel_class": hotel_class,
        "reviews": gen_reviews(),
        "terms_placement": gen_terms_placement(),
        "payment_methods": gen_payment_methods(),
        "facilities": gen_facilities(),
    }


# ─────────────────────── основная генерация ────────────────────────

def generate_dataset(n: int = 1000, filepath: str = "hotels_1k.json"):
    hotels = [gen_hotel() for _ in range(n)]

    payload = {
        "hotels": hotels,
        "provider_id": PROVIDER_ID,
        "provider_name": PROVIDER_NAME,
        "total_hotels": len(hotels),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"✅  Сгенерировано {len(hotels)} отелей → {filepath}")
    return payload


if __name__ == "__main__":
    generate_dataset(1000)