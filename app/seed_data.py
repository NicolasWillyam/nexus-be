from app.database import Base, SessionLocal, engine
from app.models.stock import Stock

# 1. Tạo tất cả các bảng trong DB nếu chưa có
Base.metadata.create_all(bind=engine)


def seed_stocks():
    db = SessionLocal()

    # Danh sách cổ phiếu mẫu khớp đúng field name của Model Stock
    sample_stocks = [
        {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "market": "NASDAQ",
            "industry": "Technology",
            "description": "Consumer electronics, software, and online services.",
            "current_price": 185.50,
            "change_amount": 2.30,
            "change_percent": 1.25,
        }
    ]

    try:
        for stock_data in sample_stocks:
            existing = (
                db.query(Stock)
                .filter(Stock.symbol == stock_data["symbol"])
                .first()
            )
            if not existing:
                stock = Stock(**stock_data)
                db.add(stock)

        db.commit()
        print("✅ Seeded initial stocks successfully!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding stocks: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_stocks()