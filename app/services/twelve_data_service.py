import os
import requests
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger("twelve_data_sync")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
BASE_URL = "https://api.twelvedata.com/stocks"

# Danh sách ưu tiên lọc Top các mã cổ phiếu nổi tiếng hàng đầu
TOP_SYMBOLS_PRIORITY = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.A", "UNH", "JNJ",
    "JPM", "V", "XOM", "PG", "MA", "HD", "CVX", "LLY", "ABBV", "BAC",
    "AVGO", "PEP", "COST", "KO", "TCM", "WMT", "CSCO", "MCD", "DIS", "AMD"
]


class TwelveDataService:

    @classmethod
    def sync_stocks_to_db(
        cls, 
        db: Session, 
        country: Optional[str] = "United States", 
        exchange: Optional[str] = None,
        limit: int = 100  # Khai báo số lượng giới hạn mặc định là 100
    ) -> Dict[str, Any]:
        if not TWELVE_DATA_API_KEY:
            raise ValueError("Thiếu TWELVE_DATA_API_KEY trong cấu hình môi trường (.env)")

        params = {"apikey": TWELVE_DATA_API_KEY}
        if country:
            params["country"] = country
        if exchange:
            params["exchange"] = exchange

        # 1. Gọi API
        logger.info(f"🌐 Đang tải danh sách từ Twelve Data...")
        try:
            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            res_json = response.json()
        except Exception as e:
            logger.error(f"❌ Lỗi HTTP: {str(e)}")
            raise RuntimeError(f"Lỗi khi kết nối Twelve Data API: {str(e)}")

        raw_stocks = res_json.get("data", [])
        total_fetched = len(raw_stocks)
        logger.info(f"📥 Đã tải về {total_fetched} mã từ API.")

        if not raw_stocks:
            return {"total_fetched": 0, "synced_count": 0, "message": "Không có dữ liệu."}

        # 2. Lọc & Sắp xếp ưu tiên để lấy Top 100
        logger.info(f"🎯 Đang lọc lấy Top {limit} mã chất lượng nhất...")
        
        # Lọc chỉ lấy các sàn chính (Bỏ qua OTC / Penny stocks)
        major_exchanges = {"NASDAQ", "NYSE"}
        filtered_stocks = []
        
        # Bước 2.1: Lọc mã thuộc sàn chính
        for item in raw_stocks:
            ex = (item.get("exchange") or "").upper()
            if not exchange and ex not in major_exchanges:
                continue  # Bỏ qua các sàn không thuộc NASDAQ / NYSE
            filtered_stocks.append(item)

        # Bước 2.2: Sắp xếp ưu tiên (Mã nằm trong danh sách HOT hoặc Mã ngắn 2-4 ký tự đưa lên trước)
        def sort_key(item):
            sym = str(item.get("symbol", "")).strip().upper()
            if sym in TOP_SYMBOLS_PRIORITY:
                return (0, TOP_SYMBOLS_PRIORITY.index(sym)) # Ưu tiên số 1
            return (1, len(sym)) # Ưu tiên số 2: Độ dài mã ngắn

        filtered_stocks.sort(key=sort_key)

        # 3. Cắt đúng `limit` bản ghi (Top 100)
        top_stocks = filtered_stocks[:limit]

        records = []
        for item in top_stocks:
            symbol = str(item.get("symbol", "")).strip()[:30]
            company_name = str(item.get("name", "")).strip()[:255]
            exchange_val = (item.get("exchange") or "").strip()
            country_val = (item.get("country") or "").strip()
            market_str = f"{exchange_val} ({country_val})" if exchange_val and country_val else (exchange_val or country_val)
            type_str = (item.get("type") or "").strip()

            records.append({
                "symbol": symbol,
                "company_name": company_name,
                "market": market_str[:100] if market_str else None,
                "industry": type_str[:255] if type_str else None,
            })

        logger.info(f"✨ Đã chọn lọc thành công Top {len(records)} mã cổ phiếu hàng đầu.")

        # 4. Upsert vào Database (Ghi duy nhất 100 bản ghi)
        upsert_query = text("""
            INSERT INTO stocks (public_id, symbol, company_name, market, industry, current_price, change_amount, change_percent)
            VALUES (gen_random_uuid(), :symbol, :company_name, :market, :industry, 0.0, 0.0, 0.0)
            ON CONFLICT (symbol) DO UPDATE 
            SET company_name = EXCLUDED.company_name,
                market = EXCLUDED.market,
                industry = EXCLUDED.industry;
        """)

        db.execute(upsert_query, records)
        db.commit()

        logger.info(f"🎉 HOÀN THÀNH! Đã đồng bộ đúng Top {len(records)} mã cổ phiếu vào DB.")
        return {
            "total_fetched": total_fetched,
            "synced_count": len(records),
            "status": "success"
        }