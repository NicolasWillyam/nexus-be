import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.data_cleaner import DataCleanerService
from app.services.financial_analytics import StockAnalyticsService
from app.services.portfolio_engine import PortfolioEngineService
from app.services.ai_explanation import AIExplanationService

logger = logging.getLogger("cluster5_orchestrator")
logger.setLevel(logging.INFO)


class PipelineOrchestrator:
    """
    Module 5.1: Điều phối luồng xử lý toàn hệ thống (End-to-End Pipeline)
    Data Fetcher (Cluster 1) -> Analysis (Cluster 2) -> Scoring & Allocation (Cluster 3) -> AI Explanation (Cluster 4)
    """

    @classmethod
    def run_stock_analysis_pipeline(
        cls, 
        db: Session, 
        symbols: List[str], 
        limit_days: int = 252
    ) -> Dict[str, Any]:
        """
        Luồng 1: Chỉ chạy Phân tích & Chấm điểm (Dùng cho trang Tổng quan Cổ phiếu)
        """
        # Step 1: Cluster 1 - Truy xuất & Làm sạch dữ liệu giá
        matrix_df = DataCleanerService.get_cleaned_price_matrix(db=db, symbols=symbols, limit_days=limit_days)
        if matrix_df.empty:
            raise ValueError("Không tìm thấy dữ liệu giá cho danh mục cổ phiếu yêu cầu.")

        # Step 2: Cluster 2 - Tính toán chỉ số Kỹ thuật & Rủi ro
        analytics_data = {}
        for symbol in matrix_df.columns:
            price_series = matrix_df[symbol].dropna()
            try:
                analytics_data[symbol] = StockAnalyticsService.analyze_single_stock(price_series)
            except Exception as e:
                logger.warning(f"Lỗi khi tính toán chỉ số cho {symbol}: {str(e)}")
                continue

        if not analytics_data:
            raise ValueError("Không thể tính toán chỉ số cho các cổ phiếu đã chọn.")

        # Step 3: Cluster 3 - Chấm điểm cổ phiếu
        scores = PortfolioEngineService.calculate_stock_scores(analytics_data)

        # Tổng hợp kết quả cho Endpoint GET /stocks/analysis
        results = {}
        for sym in analytics_data:
            results[sym] = {
                "score": scores.get(sym, 0.0),
                "metrics": analytics_data[sym]
            }

        return {
            "total_analyzed": len(results),
            "stocks": results
        }

    @classmethod
    def run_full_allocation_pipeline(
        cls, 
        db: Session, 
        symbols: List[str], 
        total_investment: float,
        apply_cap_percent: float = 35.0
    ) -> Dict[str, Any]:
        """
        Luồng 2: Chạy toàn bộ Pipeline bao gồm cả Phân bổ vốn và Gọi AI Giải thích
        """
        # Step 1 & Step 2: Lấy Matrix và Tính toán Analytics
        analysis_summary = cls.run_stock_analysis_pipeline(db=db, symbols=symbols)
        analytics_data = {sym: data["metrics"] for sym, data in analysis_summary["stocks"].items()}
        scores = {sym: data["score"] for sym, data in analysis_summary["stocks"].items()}

        # Step 3: Cluster 3 - Phân bổ vốn theo thuật toán Iterative Cap
        allocation_result = PortfolioEngineService.allocate_portfolio(
            scores=scores, 
            total_investment=total_investment
        )

        portfolio_payload = {
            "scores": scores,
            "allocation": allocation_result
        }

        # Step 4: Cluster 4 - Gọi AI Sinh bài viết giải thích
        ai_result = AIExplanationService.generate_explanation(
            portfolio_data=portfolio_payload,
            analytics_data=analytics_data
        )

        return {
            "scores": scores,
            "allocation": allocation_result,
            "ai_explanation": ai_result["explanation_markdown"],
            "ai_metadata": {
                "is_ai_generated": ai_result["is_ai_generated"],
                "guardrail_passed": ai_result["guardrail_passed"],
                "validation_errors": ai_result["validation_errors"]
            }
        }