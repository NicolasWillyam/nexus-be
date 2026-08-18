from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List

from app.database import get_db
from app.models.stock import Stock
from app.schemas.stock import StockResponse

router = APIRouter(
    prefix="/stocks",
    tags=["Stocks"]
)

@router.get("", response_model=List[StockResponse])
def get_all_stocks(db: Session = Depends(get_db)):
    """
    Lấy danh sách cổ phiếu hợp lệ (Đã có đủ current_price, change_amount, change_percent 
    và giá trị phải khác 0 / khác None).
    """
    stocks = (
        db.query(Stock)
        .filter(
            # 1. Kiểm tra không bị None (Null)
            Stock.current_price.isnot(None),
            Stock.change_amount.isnot(None),
            Stock.change_percent.isnot(None),
            # 2. Bỏ các mã có giá bằng 0 (chưa đồng bộ dữ liệu)
            Stock.current_price > 0
        )
        .all()
    )
    return stocks