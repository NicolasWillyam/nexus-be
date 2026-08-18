import logging
from typing import List
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.models.stock import Stock, StockPriceHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCleanerService:
    """Module 1.2: Lấy dữ liệu từ DB, làm sạch NaN/giá lỗi và tạo Price Matrix."""

    @staticmethod
    def get_cleaned_price_matrix(db: Session, symbols: List[str], limit_days: int = 252) -> pd.DataFrame:
        """
        Lấy giá đóng cửa của danh sách mã cổ phiếu từ DB và tạo Cleaned Price Matrix.
        
        :param db: Session SQLAlchemy
        :param symbols: Danh sách mã (ví dụ: ["AAPL", "MSFT", "NVDA"])
        :param limit_days: Số ngày giao dịch gần nhất (mặc định 252 ngày ~ 1 năm)
        :return: DataFrame với Index = Ngày (Date), Columns = Các Ticker
        """
        logger.info(f"🧹 [Module 1.2] Bắt đầu truy xuất và làm sạch dữ liệu cho: {symbols}")

        # 1. Lấy thông tin Stock từ DB
        stocks = db.query(Stock).filter(Stock.symbol.in_(symbols)).all()
        if not stocks:
            logger.warning("⚠️ Không tìm thấy cổ phiếu nào trong DB.")
            return pd.DataFrame()

        stock_map = {stock.id: stock.symbol for stock in stocks}
        stock_ids = list(stock_map.keys())

        # 2. Truy vấn dữ liệu lịch sử giá từ bảng stock_price_history
        query = (
            db.query(
                StockPriceHistory.stock_id,
                StockPriceHistory.date,
                StockPriceHistory.close_price
            )
            .filter(StockPriceHistory.stock_id.in_(stock_ids))
            .order_by(StockPriceHistory.date.desc())
        )

        raw_records = query.all()
        if not raw_records:
            logger.warning("⚠️ Không có dữ liệu lịch sử giá trong DB.")
            return pd.DataFrame()

        # 3. Chuyển đổi thành Pandas DataFrame
        df_raw = pd.DataFrame(raw_records, columns=["stock_id", "date", "close_price"])
        
        # Đổi stock_id thành Ticker symbol tương ứng
        df_raw["symbol"] = df_raw["stock_id"].map(stock_map)
        df_raw["close_price"] = pd.to_numeric(df_raw["close_price"], errors="coerce")

        # 4. Pivot Table để tạo Matrix: Rows = Date, Columns = Symbol
        price_matrix = df_raw.pivot(index="date", columns="symbol", values="close_price")

        # Sắp xếp theo thứ tự thời gian tăng dần
        price_matrix = price_matrix.sort_index()

        # Giới hạn số ngày lấy dữ liệu (ví dụ 252 ngày gần nhất)
        if len(price_matrix) > limit_days:
            price_matrix = price_matrix.tail(limit_days)

        # --- QUY TRÌNH LÀM SẠCH (DATA CLEANING) ---
        
        # A. Kiểm tra và xử lý giá <= 0
        price_matrix[price_matrix <= 0] = np.nan

        # B. Xử lý các ngày thiếu dữ liệu do lệch lịch nghỉ lễ
        # Forward fill (lấy giá ngày hôm trước) -> Backward fill (nếu bị thiếu ở đầu chuỗi)
        price_matrix = price_matrix.ffill().bfill()

        # C. Xóa các cột/dòng vẫn còn lỗi nếu có
        price_matrix = price_matrix.dropna(axis=1, how="all")

        logger.info(f"✅ [Module 1.2] Hoàn tất Matrix! Kích thước: {price_matrix.shape} (Dòng: Ngày, Cột: Mã)")
        return price_matrix