import numpy as np
import pandas as pd


def calculate_stock_metrics(df_prices: pd.DataFrame) -> dict:
    """Input: DataFrame giá đóng cửa 1Y đã sort cũ -> mới.

    Output: Dict các chỉ số Return, SMA, RSI, Volatility, Drawdown.
    """
    close = df_prices["close_price"]

    # 1. Return 1Y (SV01)
    return_1y = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]

    # 2. SMA 20 & SMA 50 (SV02)
    sma_20 = close.rolling(window=20).mean().iloc[-1]
    sma_50 = close.rolling(window=50).mean().iloc[-1]

    # 3. Volatility Annualized (SV04)
    daily_returns = close.pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252)

    # 4. Max Drawdown (SV05)
    cum_max = close.cummax()
    drawdown = (close - cum_max) / cum_max
    max_drawdown = drawdown.min()

    return {
        "return_1y": round(float(return_1y), 4),
        "sma_20": round(float(sma_20), 2),
        "sma_50": round(float(sma_50), 2),
        "volatility": round(float(volatility), 4),
        "max_drawdown": round(float(max_drawdown), 4),
    }