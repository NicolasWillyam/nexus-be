import logging
from typing import Dict, Any
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PortfolioPreprocessingService:
    """Module 1.3: Tính toán Returns, Annualized Expected Returns và Covariance Matrix."""

    TRADING_DAYS_PER_YEAR = 252  # Số ngày giao dịch trung bình trong 1 năm

    @classmethod
    def process_price_matrix(cls, price_matrix: pd.DataFrame) -> Dict[str, Any]:
        """
        Tiền xử lý Cleaned Price Matrix để chuẩn bị input cho Mô hình Tối ưu hóa (Cluster 2).

        :param price_matrix: DataFrame giá đóng cửa (Index: Date, Columns: Tickers)
        :return: Dict chứa daily_returns, annualized_returns, covariance_matrix, correlation_matrix
        """
        if price_matrix.empty or len(price_matrix) < 2:
            logger.error("❌ [Module 1.3] Price Matrix rỗng hoặc không đủ số dòng để tính toán.")
            raise ValueError("Price Matrix phải có ít nhất 2 ngày dữ liệu.")

        logger.info(f"⚙️ [Module 1.3] Đang tiến hành tiền xử lý dữ liệu cho {len(price_matrix.columns)} mã cổ phiếu...")

        # 1. Tính Tỷ suất lợi nhuận hàng ngày (Daily Returns / Percentage Change)
        # Công thức: R_t = (P_t - P_{t-1}) / P_{t-1}
        daily_returns = price_matrix.pct_change().dropna()

        # 2. Tính Lợi nhuận kỳ vọng trung bình hàng ngày (Daily Mean Returns)
        daily_mean_returns = daily_returns.mean()

        # 3. Quy đổi Lợi nhuận kỳ vọng sang quy mô NĂM (Annualized Expected Returns)
        # Công thức: E(R_annual) = E(R_daily) * 252
        annualized_returns = daily_mean_returns * cls.TRADING_DAYS_PER_YEAR

        # 4. Tính Ma trận Hiệp biến động theo NĂM (Annualized Covariance Matrix)
        # Đo lường mức độ rủi ro & tương quan biến động giá giữa các cặp cổ phiếu
        # Công thức: Cov_annual = Cov_daily * 252
        annualized_cov_matrix = daily_returns.cov() * cls.TRADING_DAYS_PER_YEAR

        # 5. Tính Ma trận Tương quan (Correlation Matrix)
        # Giúp quan sát hệ số tương quan [-1, 1] giữa các mã cổ phiếu
        correlation_matrix = daily_returns.corr()

        # 6. Tính Độ lệch chuẩn theo NĂM (Annualized Volatility / Risk) của từng mã
        annualized_volatility = daily_returns.std() * np.sqrt(cls.TRADING_DAYS_PER_YEAR)

        logger.info("✅ [Module 1.3] Hoàn tất tính toán Returns & Covariance Matrix.")

        return {
            "daily_returns": daily_returns,
            "annualized_returns": annualized_returns,
            "annualized_cov_matrix": annualized_cov_matrix,
            "correlation_matrix": correlation_matrix,
            "annualized_volatility": annualized_volatility,
        }