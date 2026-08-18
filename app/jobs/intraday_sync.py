import os
import sys
import time
from datetime import datetime
import requests
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.stock import Stock


def fetch_realtime_quotes_chunk(symbols: list[str]) -> dict | None:
    """
    Gọi endpoint /quote của Twelve Data theo từng nhóm nhỏ (tối đa 8 mã/request).
    """
    if not symbols:
        return None

    symbol_str = ",".join(symbols)
    url = "https://api.twelvedata.com/quote"
    params = {
        "symbol": symbol_str,
        "apikey": settings.TWELVE_DATA_API_KEY
    }

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Đang lấy giá Quote cho nhóm {len(symbols)} mã: {symbol_str}...")

    try:
        response = requests.get(url, params=params, timeout=15)
        
        # Nếu vẫn dính 429 do gọi quá nhanh
        if response.status_code == 429:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Bị dính Rate Limit (429). Tạm dừng 60 giây...")
            time.sleep(60)
            return None

        if response.status_code != 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Lỗi gọi Quote API: HTTP {response.status_code}")
            return None
            
        return response.json()
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Lỗi kết nối Quote API: {e}")
        return None


def run_intraday_sync():
    print(f"\n==================================================")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚡ Bắt đầu đồng bộ giá Intraday (Realtime)...")
    print(f"==================================================")

    db: Session = SessionLocal()
    try:
        stocks = db.query(Stock).all()
        if not stocks:
            print("⚠️ Không có cổ phiếu nào trong DB.")
            return

        stock_map = {stock.symbol: stock for stock in stocks}
        all_symbols = list(stock_map.keys())

        # 1. Chia 100 mã thành các nhóm nhỏ (Chunk 8 mã - giới hạn Twelve Data Free)
        CHUNK_SIZE = 8
        symbol_chunks = [all_symbols[i:i + CHUNK_SIZE] for i in range(0, len(all_symbols), CHUNK_SIZE)]

        updated_count = 0

        # 2. Duyệt từng nhóm
        for chunk_idx, chunk in enumerate(symbol_chunks, 1):
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 Nhóm [{chunk_idx}/{len(symbol_chunks)}]: {chunk}")

            quotes_data = fetch_realtime_quotes_chunk(chunk)
            if not quotes_data:
                continue

            for symbol in chunk:
                stock_obj = stock_map[symbol]
                
                # Khi request 1 mã -> dict 1 cấp; Nhiều mã -> dict lồng theo Symbol
                data = quotes_data.get(symbol, {}) if len(chunk) > 1 else quotes_data

                if "close" not in data:
                    err_msg = data.get("message", "Không có dữ liệu price")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ [{symbol}] Bỏ qua ({err_msg})")
                    continue

                try:
                    current_price = float(data["close"])
                    change_amount = float(data.get("change", 0.0))
                    change_percent = float(data.get("percent_change", 0.0))

                    # Update dữ liệu vào ORM Object
                    stock_obj.current_price = round(current_price, 2)
                    stock_obj.change_amount = round(change_amount, 2)
                    stock_obj.change_percent = round(change_percent, 2)

                    updated_count += 1
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 [{symbol}] "
                        f"Giá: ${current_price:.2f} | Biến động: {change_amount:+.2f} ({change_percent:+.2f}%)"
                    )
                except (ValueError, TypeError) as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ [{symbol}] Lỗi ép kiểu dữ liệu: {e}")

            # Lưu vào DB theo từng chunk
            db.commit()

            # Tạm dừng 8 giây giữa các chunk để không bị vượt quá 8 requests/phút
            if chunk_idx < len(symbol_chunks):
                time.sleep(8)

        print(f"\n--------------------------------------------------")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 Cập nhật hoàn tất cho {updated_count}/{len(all_symbols)} cổ phiếu.")
        print(f"==================================================\n")

    except Exception as e:
        db.rollback()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Lỗi Intraday Sync: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run_intraday_sync()