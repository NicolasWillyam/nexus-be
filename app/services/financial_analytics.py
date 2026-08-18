import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


class StockAnalyticsService:
    """Cluster 2: Phân tích kỹ thuật & Chỉ số rủi ro đầy đủ (SMA, RSI, MACD, Volatility, Max DD, Sharpe, Beta)."""

    # --- MODULE 2.1: PERFORMANCE ---
    @staticmethod
    def calculate_performance(price_series: pd.Series) -> dict:
        price_start = price_series.iloc[0]
        price_end = price_series.iloc[-1]
        
        total_return = (price_end - price_start) / price_start
        cumulative_returns = (price_series / price_start) - 1

        return {
            "total_return_1y": round(float(total_return), 4),
            "cumulative_returns": cumulative_returns.round(4).to_dict()
        }

    # --- MODULE 2.2: TREND INDICATORS (Bổ sung MACD) ---
    @staticmethod
    def calculate_trend_indicators(price_series: pd.Series) -> dict:
        # 1. SMA 20 & SMA 50
        sma_20 = price_series.rolling(window=20).mean()
        sma_50 = price_series.rolling(window=50).mean()

        # 2. RSI 14
        delta = price_series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs))

        latest_rsi = float(rsi_14.iloc[-1]) if not np.isnan(rsi_14.iloc[-1]) else 50.0
        rsi_status = "OVERBOUGHT" if latest_rsi >= 70 else ("OVERSOLD" if latest_rsi <= 30 else "NEUTRAL")

        # 3. MACD (12, 26, 9)
        ema_12 = price_series.ewm(span=12, adjust=False).mean()
        ema_26 = price_series.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        latest_macd = float(macd_line.iloc[-1])
        latest_signal = float(signal_line.iloc[-1])

        return {
            "sma_20": round(float(sma_20.iloc[-1]), 2) if not np.isnan(sma_20.iloc[-1]) else None,
            "sma_50": round(float(sma_50.iloc[-1]), 2) if not np.isnan(sma_50.iloc[-1]) else None,
            "rsi_14": round(latest_rsi, 2),
            "rsi_status": rsi_status,
            "macd": {
                "macd_line": round(latest_macd, 4),
                "signal_line": round(latest_signal, 4),
                "histogram": round(float(macd_hist.iloc[-1]), 4),
                "is_bullish": bool(latest_macd > latest_signal)
            }
        }

    # --- MODULE 2.3: RISK METRICS (Bổ sung Beta) ---
    @staticmethod
    def calculate_risk_metrics(
        price_series: pd.Series, 
        market_series: Optional[pd.Series] = None, 
        risk_free_rate: float = 0.03
    ) -> dict:
        daily_returns = price_series.pct_change().dropna()

        # 1. Volatility
        annual_volatility = daily_returns.std() * np.sqrt(252)

        # 2. Maximum Drawdown
        cum_max = price_series.cummax()
        drawdown = (price_series - cum_max) / cum_max
        max_drawdown = drawdown.min()

        # 3. Sharpe Ratio
        annual_return = daily_returns.mean() * 252
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0.0

        # 4. Beta (Tính độ tương quan với chỉ số thị trường, ví dụ SPY/VNIndex)
        beta = 1.0
        if market_series is not None and not market_series.empty:
            market_returns = market_series.pct_change().dropna()
            combined = pd.concat([daily_returns, market_returns], axis=1, join="inner").dropna()
            
            if len(combined) > 10:
                cov_matrix = np.cov(combined.iloc[:, 0], combined.iloc[:, 1])
                stock_cov_market = cov_matrix[0][1]
                market_variance = cov_matrix[1][1]
                beta = stock_cov_market / market_variance if market_variance > 0 else 1.0

        return {
            "annual_volatility": round(float(annual_volatility), 4),
            "max_drawdown": round(float(max_drawdown), 4),
            "sharpe_ratio": round(float(sharpe_ratio), 2),
            "beta": round(float(beta), 2)
        }

    # --- HÀM TỔNG HỢP ---
    @classmethod
    def analyze_single_stock(
        cls, 
        price_series: pd.Series, 
        market_series: Optional[pd.Series] = None
    ) -> dict:
        if len(price_series) < 50:
            raise ValueError("Cần tối thiểu 50 ngày dữ liệu giá để thực hiện phân tích.")

        performance = cls.calculate_performance(price_series)
        indicators = cls.calculate_trend_indicators(price_series)
        risk = cls.calculate_risk_metrics(price_series, market_series=market_series)

        return {
            "performance": performance,
            "trend_indicators": indicators,
            "risk_metrics": risk
        }