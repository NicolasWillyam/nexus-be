import os
import sys
import time
from datetime import datetime
import requests
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.stock import Stock, StockPriceHistory


def fetch_twelve_data_chunk(symbols: list[str]) -> dict | None:
    """Gọi API Twelve Data cho một nhóm nhỏ (Chunk) mã cổ phiếu (Tối đa 8 mã/request)."""
    if not symbols:
        return None

    symbol_str = ",".join(symbols)
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol_str,
        "interval": "1day",
        "outputsize": 252,
        "apikey": settings.TWELVE_DATA_API_KEY
    }

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📡 Đang tải giá cho nhóm {len(symbols)} mã: {symbol_str}...")

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 429:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Bị dính Rate Limit (429). Tạm dừng 60s để reset API quota...")
            time.sleep(60)
            return None
        
        if response.status_code != 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ API Gọi thất bại với HTTP status: {response.status_code}")
            return None
            
        return response.json()
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Ngoại lệ khi gọi API: {e}")
        return None


def run_daily_sync():
    print(f"\n==================================================")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Bắt đầu tiến trình đồng bộ dữ liệu giá cổ phiếu...")
    print(f"==================================================")

    db: Session = SessionLocal()
    try:
        # 1. Lấy danh sách cổ phiếu trong DB
        stocks = db.query(Stock).all()
        if not stocks:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Không tìm thấy cổ phiếu nào trong bảng 'stocks'. Hãy chạy seed_data trước.")
            return

        stock_map = {stock.symbol: stock.id for stock in stocks}
        all_symbols = list(stock_map.keys())
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Tìm thấy {len(all_symbols)} cổ phiếu trong DB.")

        # 2. Chia nhỏ danh sách thành từng nhóm 8 mã (Giới hạn của Twelve Data Free)
        CHUNK_SIZE = 8
        symbol_chunks = [all_symbols[i:i + CHUNK_SIZE] for i in range(0, len(all_symbols), CHUNK_SIZE)]

        total_records_processed = 0

        # 3. Lặp qua từng Chunk
        for chunk_idx, chunk in enumerate(symbol_chunks, 1):
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 Đang xử lý Nhóm [{chunk_idx}/{len(symbol_chunks)}]: {chunk}")
            
            api_data = fetch_twelve_data_chunk(chunk)
            if not api_data:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Bỏ qua nhóm này do không nhận được dữ liệu.")
                continue

            # Duyệt từng symbol trong chunk
            for symbol in chunk:
                stock_id = stock_map[symbol]
                
                # Cấu trúc JSON trả về khác nhau khi request 1 mã vs Nhiều mã
                if len(chunk) == 1:
                    stock_data = api_data
                else:
                    stock_data = api_data.get(symbol, {})

                if "values" not in stock_data:
                    err_msg = stock_data.get("message", "Không có dữ liệu values")
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  {symbol}: Bỏ qua ({err_msg})")
                    continue

                raw_values = stock_data["values"]
                records_to_upsert = []

                for row in raw_values:
                    try:
                        records_to_upsert.append({
                            "stock_id": stock_id,
                            "date": row["datetime"],
                            "open_price": float(row["open"]),
                            "high_price": float(row["high"]),
                            "low_price": float(row["low"]),
                            "close_price": float(row["close"]),
                            "volume": int(row["volume"]),
                        })
                    except (ValueError, KeyError):
                        continue

                if not records_to_upsert:
                    continue

                # 4. Upsert DB
                stmt = insert(StockPriceHistory).values(records_to_upsert)
                stmt = stmt.on_conflict_do_update(
                    constraint="uix_stock_date",
                    set_={
                        "open_price": stmt.excluded.open_price,
                        "high_price": stmt.excluded.high_price,
                        "low_price": stmt.excluded.low_price,
                        "close_price": stmt.excluded.close_price,
                        "volume": stmt.excluded.volume,
                    },
                )

                db.execute(stmt)
                count = len(records_to_upsert)
                total_records_processed += count
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {symbol}: Đã lưu {count} ngày lịch sử giá.")

            db.commit()

            # Nghỉ 8 giây giữa các chunk để không bị quá 8 requests/phút
            if chunk_idx < len(symbol_chunks):
                time.sleep(8)

        print(f"\n--------------------------------------------------")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 HOÀN THÀNH! Đã lưu tổng cộng {total_records_processed} bản ghi lịch sử giá vào DB.")
        print(f"==================================================\n")

    except Exception as e:
        db.rollback()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Lỗi tiến trình đồng bộ Database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run_daily_sync()