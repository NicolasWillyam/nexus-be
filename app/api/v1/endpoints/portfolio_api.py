from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.database import SessionLocal
from app.schemas.portfolio import (
    StockAnalysisResponse, 
    PortfolioAllocationRequest, 
    PortfolioAllocationResponse
)
from app.services.pipeline_orchestrator import PipelineOrchestrator

router = APIRouter(prefix="", tags=["Core Application API"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get(
    "/stocks/analysis", 
    response_model=StockAnalysisResponse,
    summary="Lấy chỉ số phân tích & điểm số cổ phiếu",
    description="Endpoint tính toán và trả về các chỉ số kỹ thuật (RSI, MACD), chỉ số rủi ro (Sharpe, Beta) và Stock Score."
)
def get_stock_analysis(
    symbols: List[str] = Query(..., example=["AAPL", "MSFT", "NVDA"]),
    db: Session = Depends(get_db)
):
    try:
        result = PipelineOrchestrator.run_stock_analysis_pipeline(db=db, symbols=symbols)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi hệ thống: {str(e)}")


@router.post(
    "/portfolio/allocate", 
    response_model=PortfolioAllocationResponse,
    summary="Phân bổ vốn đầu tư & AI giải thích",
    description="Endpoint nhận vốn đầu tư, tự động phân bổ vốn (Cap 35%) và gọi AI Advisor sinh bài viết giải thích có Guardrails."
)
def allocate_portfolio(
    payload: PortfolioAllocationRequest,
    db: Session = Depends(get_db)
):
    try:
        result = PipelineOrchestrator.run_full_allocation_pipeline(
            db=db,
            symbols=payload.symbols,
            total_investment=payload.total_investment
        )
        return {
            "status": "success",
            "scores": result["scores"],
            "allocation": result["allocation"],
            "ai_explanation": result["ai_explanation"],
            "ai_metadata": result["ai_metadata"]
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi hệ thống: {str(e)}")