from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class StockAnalysisResponse(BaseModel):
    total_analyzed: int
    stocks: Dict[str, Any]


class PortfolioAllocationRequest(BaseModel):
    symbols: List[str] = Field(..., example=["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"], description="Danh sách mã cổ phiếu")
    total_investment: float = Field(..., gt=0, example=10000.0, description="Tổng số tiền đầu tư ($)")


class AIMetadata(BaseModel):
    is_ai_generated: bool
    guardrail_passed: bool
    validation_errors: List[str]


class PortfolioAllocationResponse(BaseModel):
    status: str = "success"
    scores: Dict[str, float]
    allocation: Dict[str, Any]
    ai_explanation: str
    ai_metadata: AIMetadata