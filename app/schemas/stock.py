from pydantic import BaseModel
from typing import Optional

class StockResponse(BaseModel):
    id: int
    symbol: str
    company_name: str
    market: Optional[str] = None
    industry: Optional[str] = None
    current_price: Optional[float] = 0.0
    change_amount: Optional[float] = 0.0
    change_percent: Optional[float] = 0.0

    class Config:
        from_attributes = True