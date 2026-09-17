from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.data_cleaner import DataCleanerService
from app.services.financial_analytics import StockAnalyticsService
from app.services.portfolio_engine import PortfolioEngineService
from app.services.ai_explanation import AIExplanationService

router = APIRouter(prefix="/portfolio", tags=["Scoring & Portfolio Allocation"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class OptimizeRequest(BaseModel):
    symbols: List[str] = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
    total_investment: float = 10000.0
    apply_cap_percent: float = 35.0

@router.post("/portfolio/optimize", summary="Tối ưu vốn thuần toán học (Không gọi AI)")
def optimize_portfolio_only(payload: OptimizeRequest, db: Session = Depends(get_db)):
    """
    Chỉ thực hiện tính toán chấm điểm và phân bổ vốn theo thuật toán Iterative Cap 35%.
    Tốc độ phản hồi cực nhanh (< 100ms) do không chờ LLM.
    """
    matrix_df = DataCleanerService.get_cleaned_price_matrix(db=db, symbols=payload.symbols)
    analytics_data = {
        sym: StockAnalyticsService.analyze_single_stock(matrix_df[sym].dropna()) 
        for sym in matrix_df.columns
    }
    
    scores = PortfolioEngineService.calculate_stock_scores(analytics_data)
    allocation = PortfolioEngineService.allocate_portfolio(
        scores=scores, 
        total_investment=payload.total_investment
    )
    
    return {
        "status": "success",
        "scores": scores,
        "allocation": allocation
    }
@router.get("/optimize-with-ai")
def optimize_portfolio_with_ai_explanation(
    symbols: List[str] = Query(default=["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]),
    investment_amount: float = Query(default=10000.0, description="Tổng số tiền đầu tư ($)"),
    db: Session = Depends(get_db)
):
    """
    API Tích hợp toàn diện:
    - Cluster 1: Clean Price Matrix
    - Cluster 2: Technical & Risk Analytics
    - Cluster 3: Stock Scoring & Iterative Reallocation (Cap 35%)
    - Cluster 4: AI Explanation Services với Guardrails & Fallback
    """
    # 1. Cluster 1: Lấy dữ liệu giá làm sạch
    matrix_df = DataCleanerService.get_cleaned_price_matrix(db=db, symbols=symbols, limit_days=252)
    if matrix_df.empty:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu giá trong hệ thống.")

    # 2. Cluster 2: Phân tích chỉ số
    analytics_data = {}
    for symbol in matrix_df.columns:
        price_series = matrix_df[symbol].dropna()
        try:
            analytics_data[symbol] = StockAnalyticsService.analyze_single_stock(price_series)
        except Exception:
            continue

    if not analytics_data:
        raise HTTPException(status_code=500, detail="Không đủ dữ liệu để tính toán phân tích chỉ số.")

    # 3. Cluster 3: Chấm điểm & Phân bổ vốn
    stock_scores = PortfolioEngineService.calculate_stock_scores(analytics_data)
    allocation_result = PortfolioEngineService.allocate_portfolio(
        scores=stock_scores, 
        total_investment=investment_amount
    )

    portfolio_data = {
        "scores": stock_scores,
        "allocation": allocation_result
    }

    # 4. Cluster 4: Sinh bài giải thích từ AI Advisor
    ai_result = AIExplanationService.generate_explanation(
        portfolio_data=portfolio_data,
        analytics_data=analytics_data
    )

    return {
        "status": "success",
        "scores": stock_scores,
        "allocation": allocation_result,
        "ai_explanation": ai_result["explanation_markdown"],
        "ai_metadata": {
            "is_ai_generated": ai_result["is_ai_generated"],
            "guardrail_passed": ai_result["guardrail_passed"],
            "validation_errors": ai_result["validation_errors"]
        }
    }
@router.get("/{portfolio_id}/factors")
def get_portfolio_factors(portfolio_id: str):
    """
    [SV11] API lấy dữ liệu Factor Chart (Quality, Momentum, Value, Risk)
    """
    return {
        "portfolio_id": portfolio_id,
        "factors": [
            {"factor": "Quality", "score": 95},
            {"factor": "Momentum", "score": 90},
            {"factor": "Value", "score": 80},
            {"factor": "Risk", "score": 75}
        ]
    }
