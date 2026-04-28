# Tripify. ML Part

## Установка

```bash
# Из корня проекта tripify/
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# macOS Apple Silicon — дополнительно:
brew install libomp
```

## Обучение модели

```bash
python -m ranking.train
```

Модель сохранится в `models/hotel_ranker_v1.lgb`.

## Запуск API сервера

```bash
uvicorn ranking.server:app --host 0.0.0.0 --port 8080 --reload
```

Swagger UI: [http://localhost:8080/docs](http://localhost:8080/docs)

## Пример запроса

```bash
curl -X POST http://localhost:8080/rank \
  -H "Content-Type: application/json" \
  -d '{
    "api_response": {
      "hotels": [
        {
          "hid": "h1",
          "price": 150,
          "currency": "USD",
          "hotel_class": 4,
          "latitude": 40.71,
          "longitude": -74.01,
          "reviews": {"rating": 8.5, "count": 200},
          "facilities": [{"facility_name": "WiFi", "is_free": true}],
          "terms_placement": {"cancelation": true, "refund": true},
          "payment_methods": ["USD"]
        }
      ]
    },
    "user_context": {
      "user_lat": 40.7128,
      "user_lng": -74.006,
      "vacation_type": "couple",
      "budget_tier": "mid",
      "preferred_currency": "USD"
    },
    "top_k": 10
  }'
```

## Тесты

```bash
pytest ranking/tests/ -v
```

## Извлечение тегов из отзывов

Ноутбук `extract_tags.ipynb` — извлечение ключевых тегов из текстов отзывов отелей.

```bash
jupyter notebook ranking/extract_tags.ipynb
```
