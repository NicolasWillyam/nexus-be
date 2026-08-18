from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.data_cleaner import DataCleanerService
from app.services.portfolio_preprocessing import PortfolioPreprocessingService

from app.models.stock import Stock, StockPriceHistory

router = APIRouter(prefix="/data-pipeline", tags=["Data Preprocessing"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/data-pipeline/health", summary="Kiểm tra độ tươi của dữ liệu giá (Data Freshness)")
def check_data_health(db: Session = Depends(get_db)):
    """
    Kiểm tra xem dữ liệu giá cổ phiếu trong Database có được cập nhật mới nhất không.
    """
    latest_record = db.query(StockPriceHistory).order_by(StockPriceHistory.date.desc()).first()
    if not latest_record:
        return {"status": "unhealthy", "message": "Chưa có dữ liệu giá trong Database."}
    
    return {
        "status": "healthy",
        "latest_price_date": latest_record.date.strftime("%Y-%m-%d"),
        "total_records": db.query(StockPriceHistory).count()
    }

@router.get("/cleaned-price-matrix")
def get_price_matrix(
    symbols: List[str] = Query(default=["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]),
    days: int = Query(default=252, description="Số ngày giao dịch cần lấy"),
    db: Session = Depends(get_db)
):
    """API lấy Cleaned Price Matrix đã qua xử lý từ Database."""
    matrix_df = DataCleanerService.get_cleaned_price_matrix(db=db, symbols=symbols, limit_days=days)

    if matrix_df.empty:
        raise HTTPException(status_code=404, detail="Không thể tạo Price Matrix từ dữ liệu DB.")

    # Convert DataFrame thành định dạng JSON chuẩn cho Frontend/Cluster khác dễ sử dụng
    return {
        "status": "success",
        "trading_days_count": len(matrix_df),
        "symbols": list(matrix_df.columns),
        "data": matrix_df.reset_index().to_dict(orient="records")
    }

@router.get("/portfolio-inputs")
def get_portfolio_inputs(
    symbols: List[str] = Query(default=["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]),
    days: int = Query(default=252, description="Số ngày giao dịch cần lấy"),
    db: Session = Depends(get_db)
):
    """
    API Preprocessing hoàn chỉnh cho Cluster 2 (Optimization Engine).
    Trả về Lợi nhuận kỳ vọng (Expected Returns) và Ma trận rủi ro (Covariance Matrix).
    """
    # Bước 1: Lấy Cleaned Price Matrix từ DB (Module 1.2)
    matrix_df = DataCleanerService.get_cleaned_price_matrix(db=db, symbols=symbols, limit_days=days)

    if matrix_df.empty:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu giá phù hợp trong DB.")

    # Bước 2: Chạy Preprocessing tính toán Returns & Covariance (Module 1.3)
    processed_data = PortfolioPreprocessingService.process_price_matrix(matrix_df)

    # Convert dữ liệu Pandas sang định dạng JSON gọn nhẹ cho API
    return {
        "status": "success",
        "symbols": list(matrix_df.columns),
        "trading_days": len(matrix_df),
        # Lợi nhuận kỳ vọng theo năm của từng mã (%)
        "expected_returns_annual": (processed_data["annualized_returns"] * 100).round(2).to_dict(),
        # Độ biến động rủi ro theo năm của từng mã (%)
        "volatility_annual": (processed_data["annualized_volatility"] * 100).round(2).to_dict(),
        # Ma trận Hiệp biến động (Covariance Matrix)
        "covariance_matrix": processed_data["annualized_cov_matrix"].round(6).to_dict(),
        # Ma trận Tương quan (Correlation Matrix)
        "correlation_matrix": processed_data["correlation_matrix"].round(4).to_dict(),
    }