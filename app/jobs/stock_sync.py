"""
Script đồng bộ danh sách mã cổ phiếu từ Twelve Data vào Cơ sở dữ liệu.
Sử dụng độc lập cho CLI / Cronjob hệ thống:
    python stock_sync.py [--country "United States"] [--exchange "NASDAQ"]
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# Đảm bảo Python nhận diện được các module trong thư mục app/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from app.database import SessionLocal
from app.services.twelve_data_service import TwelveDataService

# 1. Cấu hình Logging ra cả Console và file log riêng
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"stock_sync_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("stock_sync_cli")


def run_stock_sync(country: str = "United States", exchange: str = None):
    """
    Hàm khởi tạo DB Session và thực thi lệnh đồng bộ từ TwelveDataService.
    """
    logger.info("==================================================")
    logger.info(f"🚀 BẮT ĐẦU ĐỒNG BỘ MÃ CỔ PHIẾU (Country='{country}', Exchange='{exchange}')")
    logger.info("==================================================")

    # Load biến môi trường từ .env
    load_dotenv()

    # Tạo DB Session
    db = SessionLocal()
    try:
        start_time = datetime.now()
        
        # Gọi Service đồng bộ
        result = TwelveDataService.sync_stocks_to_db(
            db=db, 
            country=country, 
            exchange=exchange
        )

        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ THÀNH CÔNG! Đã tải & đồng bộ {result.get('total_fetched', 0)} bản ghi.")
        logger.info(f"⏱️  Thời gian xử lý: {execution_time:.2f} giây.")

    except Exception as e:
        logger.error(f"❌ THẤT BẠI! Lỗi xảy ra trong quá trình đồng bộ: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()
        logger.info("🔒 Đã đóng kết nối Database.")


if __name__ == "__main__":
    # 2. Cấu hình Tham số Dòng lệnh (CLI Arguments)
    parser = argparse.ArgumentParser(description="Tool đồng bộ mã chứng khoán từ Twelve Data vào DB")
    parser.add_argument(
        "--country", 
        type=str, 
        default="United States", 
        help="Quốc gia muốn lấy mã cổ phiếu (Mặc định: 'United States')"
    )
    parser.add_argument(
        "--exchange", 
        type=str, 
        default=None, 
        help="Sàn giao dịch muốn lọc (Ví dụ: 'NASDAQ', 'NYSE'). Mặc định: Lấy tất cả"
    )

    args = parser.parse_args()
    
    # Chạy hàm chính
    run_stock_sync(country=args.country, exchange=args.exchange)