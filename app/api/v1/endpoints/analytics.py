from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.data_cleaner import DataCleanerService
from app.services.financial_analytics import StockAnalyticsService

router = APIRouter(prefix="/analytics", tags=["Stock Financial Analytics"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/stock-summary")
def get_stock_analytics(
    symbols: List[str] = Query(default=["AAPL", "MSFT", "NVDA", "AMZN"]),
    benchmark_symbol: str = Query(default="AAPL", description="Mã cổ phiếu làm tham chiếu thị trường để tính Beta"),
    days: int = Query(default=252, description="Số ngày dữ liệu lịch sử"),
    db: Session = Depends(get_db)
):
    # Đảm bảo benchmark_symbol có trong query DB
    query_symbols = list(set(symbols + [benchmark_symbol]))
    matrix_df = DataCleanerService.get_cleaned_price_matrix(db=db, symbols=query_symbols, limit_days=days)

    if matrix_df.empty:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu giá trong Database.")

    # Tách chuỗi giá thị trường benchmark
    market_series = matrix_df[benchmark_symbol] if benchmark_symbol in matrix_df.columns else None

    results = {}
    for symbol in symbols:
        if symbol not in matrix_df.columns:
            continue

        price_series = matrix_df[symbol].dropna()
        try:
            analysis = StockAnalyticsService.analyze_single_stock(
                price_series=price_series, 
                market_series=market_series if symbol != benchmark_symbol else None
            )
            results[symbol] = analysis
        except ValueError as e:
            results[symbol] = {"error": str(e)}

    return {
        "status": "success",
        "benchmark_used": benchmark_symbol,
        "analyzed_stocks_count": len(results),
        "data": results
    }