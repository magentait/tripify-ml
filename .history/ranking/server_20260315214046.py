# server.py
"""
REST API server for hotel ranking.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging
import uvicorn

from ranker import HotelRanker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hotel Ranking Service",
    version="1.0.0",
    description="ML-powered hotel ranking for travel applications",
)

# Global ranker instance
ranker = HotelRanker(model_dir="models")


@app.on_event("startup")
async def startup():
    ranker.load_model("hotel_ranker_v1")
    logger.info("Hotel ranker model loaded and ready")


# ------------------------------------------------------------------ #
#  Request / Response models                                           #
# ------------------------------------------------------------------ #

class UserContext(BaseModel):
    user_lat: Optional[float] = None
    user_lng: Optional[float] = None
    vacation_type: Optional[str] = None  # family | business | solo | couple
    budget_tier: Optional[str] = None    # low | mid | high
    preferred_currency: Optional[str] = None


class BusinessRules(BaseModel):
    boost_cancellable: float = 0.0
    penalize_no_reviews: float = 0.0
    min_rating: Optional[float] = None
    sponsored_hids: list[int] = Field(default_factory=list)


class RankRequest(BaseModel):
    api_response: dict
    user_context: Optional[UserContext] = None
    top_k: Optional[int] = None
    business_rules: Optional[BusinessRules] = None


class RankResponse(BaseModel):
    hotels: list[dict]
    total: int
    model_version: str = "hotel_ranker_v1"


# ------------------------------------------------------------------ #
#  Endpoints                                                           #
# ------------------------------------------------------------------ #

@app.post("/rank", response_model=RankResponse)
async def rank_hotels(request: RankRequest):
    """Rank hotels from provider API response."""
    try:
        user_ctx = request.user_context.dict() if request.user_context else None
        rules = request.business_rules.dict() if request.business_rules else None

        ranked = ranker.rank(
            api_response=request.api_response,
            user_context=user_ctx,
            top_k=request.top_k,
            business_rules=rules,
        )

        return RankResponse(
            hotels=ranked,
            total=len(ranked),
        )
    except Exception as e:
        logger.exception("Ranking failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": ranker.model is not None,
        "num_features": len(ranker.feature_names),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)