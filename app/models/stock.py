import uuid
from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )

    # Nâng cấp độ dài tối đa cho các cột chuỗi
    symbol = Column(String(30), unique=True, nullable=False, index=True) # Nâng từ 10 -> 30
    company_name = Column(String(255), nullable=False)
    market = Column(String(100))      # Nâng từ 20 -> 100 (để chứa cả Exchange & Country)
    industry = Column(String(255))    # Nâng từ 100 -> 255
    description = Column(Text)

    current_price = Column(Numeric(18, 2), default=0.0)
    change_amount = Column(Numeric(18, 2), default=0.0)
    change_percent = Column(Numeric(5, 2), default=0.0)


class StockPriceHistory(Base):
    __tablename__ = "stock_price_history"

    id = Column(Integer, primary_key=True, index=True)
    # Giữ nguyên ForeignKey liên kết bằng id (Integer) nội bộ để JOIN nhanh nhất
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    open_price = Column(Numeric(18, 2))
    high_price = Column(Numeric(18, 2))
    low_price = Column(Numeric(18, 2))
    close_price = Column(Numeric(18, 2))
    volume = Column(Integer)

    __table_args__ = (
        UniqueConstraint("stock_id", "date", name="uix_stock_date"),
    )