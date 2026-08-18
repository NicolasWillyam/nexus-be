import numpy as np
import pandas as pd
from typing import Dict, List, Any


class PortfolioEngineService:
    """Cluster 3: Scoring & Portfolio Allocation Engine."""

    CAP_PER_STOCK = 0.35  # Giới hạn tối đa 35% / mã cổ phiếu

    # --- MODULE 3.1: STOCK SCORING ENGINE ---
    @classmethod
    def calculate_stock_scores(cls, analytics_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Chuẩn hóa các chỉ số kỹ thuật/rủi ro từ Cluster 2 về thang điểm 0 - 100.
        """
        symbols = list(analytics_data.keys())
        if not symbols:
            return {}

        # Trích xuất dữ liệu thành DataFrame để chuẩn hóa Min-Max
        records = []
        for sym in symbols:
            item = analytics_data[sym]
            records.append({
                "symbol": sym,
                "return": item["performance"]["total_return_1y"],
                "sharpe": item["risk_metrics"]["sharpe_ratio"],
                "rsi": item["trend_indicators"]["rsi_14"],
                "is_macd_bullish": 1.0 if item["trend_indicators"]["macd"]["is_bullish"] else 0.0,
                "volatility": item["risk_metrics"]["annual_volatility"],
                "max_dd": abs(item["risk_metrics"]["max_drawdown"]),
            })

        df = pd.DataFrame(records).set_index("symbol")

        # Hàm helper chuẩn hóa Min-Max [0, 100]
        def min_max_scale(series: pd.Series, invert: bool = False) -> pd.Series:
            s_min, s_max = series.min(), series.max()
            if s_max == s_min:
                return pd.Series(50.0, index=series.index)
            scaled = (series - s_min) / (s_max - s_min) * 100.0
            return 100.0 - scaled if invert else scaled

        # 1. Return Score (35% Trọng số)
        return_score = min_max_scale(df["return"]) * 0.7 + min_max_scale(df["sharpe"]) * 0.3

        # 2. Trend Score (35% Trọng số)
        # RSI điểm cao nhất khi ở vùng lành mạnh (40 - 65)
        rsi_penalty = (df["rsi"] - 50.0).abs()
        rsi_score = min_max_scale(rsi_penalty, invert=True)
        trend_score = rsi_score * 0.6 + (df["is_macd_bullish"] * 100.0) * 0.4

        # 3. Risk Penalty (30% Trọng số) - Càng rủi ro cao điểm phạt càng lớn
        risk_score = min_max_scale(df["volatility"], invert=True) * 0.5 + min_max_scale(df["max_dd"], invert=True) * 0.5

        # Tổng hợp Stock Score (0 - 100)
        final_scores = (return_score * 0.35) + (trend_score * 0.35) + (risk_score * 0.30)
        return final_scores.round(2).to_dict()

    # --- MODULE 3.2: PORTFOLIO ALLOCATION ENGINE ---
    @classmethod
    def allocate_portfolio(
        cls, 
        scores: Dict[str, float], 
        total_investment: float = 10000.0
    ) -> Dict[str, Any]:
        """
        Phân bổ vốn $10,000 dựa trên tỷ lệ Score và áp dụng ràng buộc Cap 35%.
        """
        symbols = list(scores.keys())
        num_stocks = len(symbols)

        if num_stocks == 0:
            return {"weights": {}, "allocations": {}}

        # Nếu tổng số mã <= 2, cap 35% không thể thỏa mãn (vì 2 * 35% = 70% < 100%)
        # Tự động điều chỉnh Cap phù hợp
        effective_cap = cls.CAP_PER_STOCK
        if num_stocks * cls.CAP_PER_STOCK < 1.0:
            effective_cap = round(1.0 / num_stocks, 4)

        score_series = pd.Series(scores)
        total_score = score_series.sum()

        if total_score == 0:
            weights = pd.Series(1.0 / num_stocks, index=symbols)
        else:
            weights = score_series / total_score

        # Vòng lặp tái phân bổ phần vốn dư (Iterative Reallocation)
        capped_weights = weights.copy()
        locked_symbols = set()

        while True:
            exceeded = capped_weights[capped_weights > effective_cap]
            new_exceeded = set(exceeded.index) - locked_symbols

            if not new_exceeded:
                break  # Tất cả các mã đã thỏa mãn constraint <= effective_cap

            for sym in new_exceeded:
                capped_weights[sym] = effective_cap
                locked_symbols.add(sym)

            # Tính lại trọng số cho các mã chưa bị khóa (unlocked)
            unlocked_symbols = list(set(symbols) - locked_symbols)
            if not unlocked_symbols:
                break

            remaining_weight = 1.0 - (len(locked_symbols) * effective_cap)
            unlocked_score_sum = score_series[unlocked_symbols].sum()

            if unlocked_score_sum > 0:
                for sym in unlocked_symbols:
                    capped_weights[sym] = (score_series[sym] / unlocked_score_sum) * remaining_weight
            else:
                for sym in unlocked_symbols:
                    capped_weights[sym] = remaining_weight / len(unlocked_symbols)

        # Quy đổi ra số tiền cụ thể
        allocations = (capped_weights * total_investment).round(2)

        return {
            "total_investment": total_investment,
            "applied_cap_percent": round(effective_cap * 100, 2),
            "weights_percent": (capped_weights * 100).round(2).to_dict(),
            "amount_allocated": allocations.to_dict()
        }