.PHONY: train serve test lint

# Generate synthetic data + train model
train:
    python train.py

# Start ranking API server
serve:
    uvicorn server:app --host 0.0.0.0 --port 8080 --reload

# Run tests
test:
    pytest tests/ -v --tb=short

# Type check
lint:
    ruff check .
    mypy features.py ranker.py train.py --ignore-missing-imports