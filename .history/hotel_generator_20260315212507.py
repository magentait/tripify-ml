"""Асинхронная генерация данных отелей."""

import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from llm_client import AsyncLLMClient
from review_generator import generate_reviews_async

random.seed(42)

# ══════════════════ РЕАЛЬНЫЕ ОТЕЛИ ══════════════════

REAL_HOTELS = [
    {"title": "The Plaza Hotel", "city": "[Address223]", "country": "US", "currency": "USD",
     "address": "768 [Address224], [Address225] York, NY 10019", "lat": 40.7644, "lng": -73.9742,
     "hotel_class": 5, "price_range": (450, 1500),
     "description": "Iconic luxury hotel overlooking [Address226] Park with gilded interiors and legendary Palm Court."},
    {"title": "The Standard High Line", "city": "[Address227]", "country": "US", "currency": "USD",
     "address": "848 [Address228], [Address229], NY 10014", "lat": 40.7409, "lng": -74.0080,
     "hotel_class": 4, "price_range": (250, 700),
     "description": "Trendy hotel straddling the High Line with floor-to-ceiling windows and rooftop bar."},
    {"title": "Pod 51 Hotel", "city": "[Address230]", "country": "US", "currency": "USD",
     "address": "230 E 51st St, [Address231], NY 10022", "lat": 40.7554, "lng": -73.9690,
     "hotel_class": 3, "price_range": (90, 200),
     "description": "Compact micro-hotel in Midtown with a rooftop garden and smart-design rooms."},
    {"title": "The Savoy", "city": "London", "country": "GB", "currency": "GBP",
     "address": "Strand, London WC2R 0EZ", "lat": 51.5101, "lng": -0.1204,
     "hotel_class": 5, "price_range": (400, 1200),
     "description": "Legendary Thames-side hotel with Art Deco rooms and Kaspar's seafood bar."},
    {"title": "Premier Inn London [Address232]", "city": "London", "country": "GB", "currency": "GBP",
     "address": "[Address233] [Address234], London SE1 7NJ", "lat": 51.5028, "lng": -0.1132,
     "hotel_class": 3, "price_range": (80, 180),
     "description": "Budget-friendly hotel near Waterloo Station with clean rooms and free WiFi."},
    {"title": "Hôtel Plaza Athénée", "city": "Paris", "country": "FR", "currency": "EUR",
     "address": "[Address235] [Address236], 75008 [Address237]", "lat": 48.8660, "lng": 2.3042,
     "hotel_class": 5, "price_range": (600, 2000),
     "description": "Glamorous palace hotel with Alain Ducasse restaurant and Eiffel Tower views."},
    {"title": "Hôtel Le Marais", "city": "Paris", "country": "FR", "currency": "EUR",
     "address": "[Address238], 75003 Paris", "lat": 48.8633, "lng": 2.3644,
     "hotel_class": 3, "price_range": (120, 280),
     "description": "Charming boutique hotel in the trendy Marais with exposed beams and courtyard."},
    {"title": "Burj Al Arab Jumeirah", "city": "[Address239]", "country": "AE", "currency": "AED",
     "address": "Jumeirah St, Dubai", "lat": 25.1412, "lng": 55.1853,
     "hotel_class": 5, "price_range": (1500, 5000),
     "description": "Sail-shaped ultra-luxury hotel on its own island with duplex suites and 9 restaurants."},
    {"title": "Rove Downtown", "city": "Dubai", "country": "AE", "currency": "AED",
     "address": "[Address240] Rd, Downtown [Address241]", "lat": 25.2048, "lng": 55.2708,
     "hotel_class": 3, "price_range": (80, 200),
     "description": "Hip budget hotel with rooftop pool, Burj Khalifa views, near Dubai Mall."},
    {"title": "Park Hyatt Tokyo", "city": "Tokyo", "country": "JP", "currency": "JPY",
     "address": "3-7-1-2 [Address242]-[Address243]juku, Tokyo 163-1055", "lat": 35.6855, "lng": 139.6917,
     "hotel_class": 5, "price_range": (500, 1200),
     "description": "Elegant skyscraper hotel from Lost in Translation with indoor pool and Mt. Fuji views."},
    {"title": "Hotel Gracery [Address244]juku", "city": "Tokyo", "country": "JP", "currency": "JPY",
     "address": "1-19-1 Kabukicho, [Address245], Tokyo 160-8466", "lat": 35.6942, "lng": 139.7018,
     "hotel_class": 3, "price_range": (80, 220),
     "description": "Popular tourist hotel topped with a giant Godzilla head in Kabukicho."},
    {"title": "Four Seasons Istanbul at Sultanahmet", "city": "Istanbul", "country": "TR", "currency": "TRY",
     "address": "Tevkifhane Sk. No:1, 34122 Fatih/İstanbul", "lat": 41.0066, "lng": 28.9770,
     "hotel_class": 5, "price_range": (350, 900),
     "description": "Former Ottoman prison turned luxury hotel steps from Blue Mosque and Hagia Sophia."},
    {"title": "Hotel [Surname8] Roma", "city": "Rome", "country": "IT", "currency": "EUR",
     "address": "[Address246] 6, 00187 Roma", "lat": 41.9060, "lng": 12.4832,
     "hotel_class": 5, "price_range": (450, 1400),
     "description": "Iconic hotel atop Spanish Steps with Michelin-starred restaurant and panoramic terrace."},
    {"title": "W Barcelona", "city": "Barcelona", "country": "ES", "currency": "EUR",
     "address": "[Address247] 1, 08039 [Address248]", "lat": 41.3687, "lng": 2.1893,
     "hotel_class": 5, "price_range": (300, 900),
     "description": "Sail-shaped beachfront hotel with infinity pool and Eclipse rooftop bar."},
    {"title": "Mandarin Oriental Bangkok", "city": "Bangkok", "country": "TH", "currency": "THB",
     "address": "[Address249] [Address250], Bangkok 10500", "lat": 13.7237, "lng": 100.5155,
     "hotel_class": 5, "price_range": (300, 1000),
     "description": "Legendary riverside hotel since 1876 with Thai cooking school and award-winning spa."},
    {"title": "Lub d Bangkok Siam", "city": "Bangkok", "country": "TH", "currency": "THB",
     "address": "925/9 [Address251] Rd, Bangkok 10330", "lat": 13.7458, "lng": 100.5306,
     "hotel_class": 3, "price_range": (25, 80),
     "description": "Trendy social hostel-hotel near Siam Square with cinema room and rooftop bar."},
    {"title": "Park Hyatt [Address252]", "city": "[Address253]", "country": "AU", "currency": "AUD",
     "address": "7 Hickson Rd, Sydney NSW 2000", "lat": -33.8559, "lng": 151.2093,
     "hotel_class": 5, "price_range": (500, 1500),
     "description": "Waterfront luxury with Opera House and Harbour Bridge views, rooftop pool."},
    {"title": "Hotel Metropol Moscow", "city": "Moscow", "country": "RU", "currency": "RUB",
     "address": "[Address254] [Address255], Moscow 109012", "lat": 55.7580, "lng": 37.6218,
     "hotel_class": 5, "price_range": (200, 600),
     "description": "Art Nouveau masterpiece near Bolshoi Theatre with stained-glass ceilings."},
    {"title": "Marriott Mena House Cairo", "city": "Cairo", "country": "EG", "currency": "EGP",
     "address": "[Address256] [Address257], Giza", "lat": 29.9876, "lng": 31.1232,
     "hotel_class": 5, "price_range": (150, 500),
     "description": "Historic palace hotel at the foot of the Great Pyramids with lush gardens."},
    {"title": "Marina Bay Sands", "city": "Singapore", "country": "SG", "currency": "SGD",
     "address": "10 [Address258] Ave, Singapore 018956", "lat": 1.2834, "lng": 103.8607,
     "hotel_class": 5, "price_range": (350, 1200),
     "description": "Triple-tower icon with world's largest rooftop infinity pool and casino."},
]

# ══════════════════ СПРАВОЧНИКИ ══════════════════

FOOD_PLACES = [
    "Pool Bar", "Lobby Lounge", "Sushi Corner", "Italian Trattoria",
    "Rooftop Restaurant", "Beach Café", "BBQ Terrace", "Tapas Bar",
    "Steakhouse", "Dim Sum Palace", "French Bistro", "Seafood Grill",
]
BEACH_PLACES = [
    "Sunset Beach", "Coral Bay", "Palm Shore", "White Sand Beach",
    "Blue Lagoon", "Crystal Cove", "Golden Coast", "Marina Beach",
]
FACILITY_TYPES = [
    "transfer", "bath", "spa", "gym", "pool", "wifi", "parking",
    "restaurant", "bar", "laundry", "concierge", "room_service",
    "sauna", "kids_club", "business_center", "airport_shuttle",
]
CARD_TYPES = ["VISA", "MASTERCARD", "AMEX", "JSB", "UnionPay", "Mir"]
CURRENCIES_CASH = ["AED", "USD", "RUB", "EUR", "GBP", "TRY", "THB", "CNY"]
TIMEZONES = [
    "UTC", "Europe/London", "Europe/Paris", "Europe/Moscow",
    "America/[Address259]_York", "Asia/Dubai", "Asia/Tokyo",
]

# ══════════════════ УТИЛИТЫ ══════════════════

used_hids = set()


def gen_hid():
    while True:
        hid = random.randint(1_000_000, 9_999_999)
        if hid not in used_hids:
            used_hids.add(hid)
            return hid


def fake_uuid():
    return hashlib.md5(str(random.random()).encode()).hexdigest()


def fake_date(start_year=2023, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end - start).days))).strftime("%Y-%m-%d")


def jitter(value, pct=0.002):
    return round(value + random.uniform(-abs(value * pct), abs(value * pct)), 7)


# ══════════════════ ГЕНЕРАТОРЫ СЕКЦИЙ ══════════════════

def gen_nearby_places():
    food = [
        {"title": t, "distance": random.choice([0.1, 0.2, 0.5, 1, 1.5, 2, 3]), "unit": "km"}
        for t in random.sample(FOOD_PLACES, k=random.randint(1, 4))
    ]
    beaches = [
        {"title": t, "distance": random.choice([100, 200, 300, 500, 800, 1200]), "unit": "m"}
        for t in random.sample(BEACH_PLACES, k=random.randint(0, 3))
    ]
    return {"food": food, "beaches": beaches}


def gen_reviews_histogram(total):
    parts = [random.random() for _ in range(5)]
    s = sum(parts)
    counts = [int(total * p / s) for p in parts]
    counts[4] += total - sum(counts)
    return {str(i + 1): counts[i] for i in range(5)}


def gen_reviews_classes(hotel_class):
    base = 4.0 + hotel_class * 0.8
    return {
        k: round(min(10.0, max(1.0, random.gauss(base, 0.8))), 1)
        for k in ["cleanliness", "service", "price_quality", "room", "location"]
    }


def gen_terms_placement():
    cancelation = random.random() > 0.25
    conditions = []
    if cancelation:
        conditions.append({"quantity_percent": 100, "condition": "If cancelation before 2 days check in room"})
        if random.random() > 0.3:
            conditions.append({"quantity_percent": 50, "condition": "If cancelation before 1 day check in room"})
    return {
        "check_in": {"after_time": random.choice(["12:00", "13:00", "14:00", "15:00"]),
                      "before_time": random.choice(["00:00", "23:00", "23:59"]),
                      "timezone": random.choice(TIMEZONES)},
        "check_out": {"after_time": "00:00",
                       "before_time": random.choice(["10:00", "11:00", "12:00"]),
                       "timezone": random.choice(TIMEZONES)},
        "cancelation": cancelation,
        "refund_rule": {"refund_prepayment": cancelation, "conditions": conditions},
        "smoking": random.random() < 0.15,
        "pet_friendly": random.random() < 0.3,
        "party_friendly": random.random() < 0.15,
        "age_restriction": random.choice(["18+", "21+", "16+", None]),
        "additional_info": random.choice([None, None, "Government ID required", "Deposit required", "Quiet hours 22:00-08:00"]),
    }


def gen_payment_methods():
    is_cash = random.random() > 0.2
    is_card = random.random() > 0.1
    return {
        "cash_info": {"is_cash": is_cash,
                      "currency": random.sample(CURRENCIES_CASH, k=random.randint(1, 3)) if is_cash else []},
        "cards_info": {"is_card": is_card,
                       "card_types": random.sample(CARD_TYPES, k=random.randint(2, 4)) if is_card else []},
    }


def gen_facilities(hotel_class):
    n = random.randint(max(2, hotel_class), min(len(FACILITY_TYPES), hotel_class + 6))
    chosen = random.sample(FACILITY_TYPES, k=n)
    free_bias = 0.6 if hotel_class >= 4 else 0.35
    return [{"type": t, "is_free": random.random() < free_bias} for t in chosen]


# ══════════════════ ГЕНЕРАЦИЯ ВАРИАЦИЙ ══════════════════

async def generate_hotel_variations_async(llm, template, count=50):
    # type: (AsyncLLMClient, dict, int) -> Optional[list]
    """Просит LLM сгенерировать вариации отеля. 3 попытки."""

    messages = [
        {"role": "system", "content": "You generate realistic hotel data. Return ONLY a JSON array."},
        {"role": "user", "content": f"""Based on this real hotel, generate {count} DIFFERENT fictional hotels in the same city/region.

Real hotel: "{template['title']}" in {template['city']}, {template['country']}
Stars: {template['hotel_class']}, Price: {template['price_range'][0]}-{template['price_range'][1]} {template['currency']}

For each hotel return a JSON object:
- "title": unique realistic hotel name (NOT the original)
- "description": 1-2 sentences, unique
- "address": realistic address in that city
- "lat": latitude (vary slightly from {template['lat']})
- "lng": longitude (vary slightly from {template['lng']})
- "hotel_class": vary between {max(1, template['hotel_class']-1)} and {min(5, template['hotel_class']+1)}
- "price": integer in range {template['price_range']}

Return ONLY a JSON array of {count} objects."""}
    ]

    for attempt in range(1, 4):
        result = await llm.request_json(messages, max_tokens=6144, temperature=1.0)
        if result and isinstance(result, list) and len(result) >= count * 0.5:
            return result
        print(f"    ⚠️  Вариации: попытка {attempt}/3 не удалась")

    return None


# ══════════════════ ГЕНЕРАЦИЯ ОДНОГО ОТЕЛЯ ══════════════════

async def generate_hotel_async(llm, template, comments_count):
    # type: (AsyncLLMClient, dict, int) -> dict
    """Генерирует один отель с отзывами."""

    hid = gen_hid()
    price = random.randint(*template["price_range"])

    # Генерация отзывов через LLM
    raw_comments = await generate_reviews_async(
        llm,
        hotel_title=template["title"],
        city=template["city"],
        country=template["country"],
        hotel_class=template["hotel_class"],
        count=comments_count,
    )

    for rc in raw_comments:
        rc["review_date"] = fake_date()
        rc["photos"] = [
            {"link": f"https://cdn.hotels.com/reviews/{fake_uuid()}.jpg"}
            for _ in range(random.randint(0, 3))
        ]

    ratings = [c.get("rating", 7.0) for c in raw_comments] if raw_comments else [7.0]
    avg_rating = round(sum(ratings) / len(ratings) / 2, 1)

    return {
        "hid": hid,
        "title": template["title"],
        "link": f"https://tripify.com/hotels/{hid}",
        "description": template["description"],
        "address": template["address"],
        "gps_coordinates": {"latitude": jitter(template["lat"]), "longitude": jitter(template["lng"])},
        "city": template["city"],
        "country": template["country"],
        "currency": template["currency"],
        "price": price,
        "nearby_places": gen_nearby_places(),
        "hotel_class": template["hotel_class"],
        "reviews": {
            "total": random.randint(50, 5000),
            "rating": min(5.0, max(1.0, avg_rating)),
            "reviews_histogram": gen_reviews_histogram(random.randint(50, 5000)),
            "reviews_classes": gen_reviews_classes(template["hotel_class"]),
            "comments": raw_comments,
            "total_comments": len(raw_comments),
        },
        "terms_placement": gen_terms_placement(),
        "payment_methods": gen_payment_methods(),
        "facilities": gen_facilities(template["hotel_class"]),
    }