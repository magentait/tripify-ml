# Tripify. ML Part

## Установка

```bash
# Из корня проекта tripify/
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install -r requirements.txt

# macOS Apple Silicon — дополнительно:
brew install libomp
```

## Обучение модели ранжирования

```bash
python -m ranking.train
```

Модель сохранится в `models/hotel_ranker_v1.lgb`.

## Векторный поиск по отзывам (Qdrant)

### Запуск Qdrant

Требуется установленный Docker Desktop.

```bash
docker run -d --name qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

Дашборд: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

Остановить / запустить снова:
```bash
docker stop qdrant
docker start qdrant
```

### Индексация отзывов

```bash
python build_search_index.py
```

Скрипт эмбеддит отзывы моделью `sentence-transformers` и загружает в коллекцию `hotel_reviews`.

> При первом запуске скачивается модель эмбеддингов (~120–500 МБ в зависимости от выбранной в `search/embeddings.py`).
>
> Если HuggingFace недоступен напрямую, используй зеркало:
> ```bash
> export HF_ENDPOINT=https://hf-mirror.com
> python build_search_index.py
> ```

### Пример поиска

```bash
python try_search.py
```

Или из кода:
```python
from search.searcher import ReviewSearcher

s = ReviewSearcher()
results = s.search(
    "clean room and good breakfast",
    limit=5,
    min_rating=7.0,
)
for r in results:
    print(f"[{r['score']:.3f}] hotel={r['hotel_id']}: {r['text'][:150]}")
```

## Запуск API сервера

```bash
uvicorn ranking.server:app --host 0.0.0.0 --port 8080 --reload
```

Swagger UI: [http://localhost:8080/docs](http://localhost:8080/docs)

## Пример запроса к ранкеру

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

## Структура проекта

```
tripify/
├── ranking/              # ML-ранкер отелей (LightGBM LambdaRank)
│   ├── features.py       # извлечение фичей
│   ├── data_generator.py # синтетические данные
│   ├── train.py          # обучение
│   ├── server.py         # FastAPI
│   └── tests/
├── search/               # Векторный поиск по отзывам (Qdrant)
│   ├── embeddings.py     # модель эмбеддингов
│   ├── qdrant_setup.py   # клиент + коллекция
│   ├── indexer.py        # загрузка отзывов
│   └── searcher.py       # семантический поиск
├── build_search_index.py # скрипт индексации
├── try_search.py         # демо поиска
└── requirements.txt
```

## Структура проекта

```
tripify/
├── ranking/              # ML-ранкер отелей (LightGBM LambdaRank)
│   ├── features.py       # извлечение фичей
│   ├── data_generator.py # синтетические данные
│   ├── train.py          # обучение
│   ├── server.py         # FastAPI
│   └── tests/
├── search/               # Векторный поиск по отзывам (Qdrant)
│   ├── embeddings.py     # модель эмбеддингов
│   ├── qdrant_setup.py   # клиент + коллекция
│   ├── indexer.py        # загрузка отзывов
│   └── searcher.py       # семантический поиск
├── build_search_index.py # скрипт индексации
├── try_search.py         # демо поиска
└── requirements.txt
```
