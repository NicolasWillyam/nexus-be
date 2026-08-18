from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import 2 hàm chạy sync job
from app.jobs.daily_sync import run_daily_sync
from app.jobs.intraday_sync import run_intraday_sync

# Khởi tạo Scheduler ở background
scheduler = BackgroundScheduler()

from app.api.v1.endpoints.data_pipeline import router as pipeline_router
from app.api.v1.endpoints.stocks import router as stocks
from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.portfolio import router as portfolio_router
from app.api.v1.endpoints.portfolio_api import router as portfolio_api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------------------------------------------------------
    # 1. SETUP SCHEDULER KHI FASTAPI KHỞI ĐỘNG
    # ---------------------------------------------------------
    
    # Job 1: Lấy giá Intraday (15 phút / lần, từ T2 - T6)
    scheduler.add_job(
        run_intraday_sync,
        trigger=IntervalTrigger(minutes=15),
        id="intraday_sync_job",
        name="Đồng bộ giá chứng khoán Intraday 15 phút",
        replace_existing=True,
    )

    # Job 2: Đồng bộ Lịch sử & Giá cuối ngày (Chạy lúc 17:00 hàng ngày từ T2 - T6)
    scheduler.add_job(
        run_daily_sync,
        trigger=CronTrigger(day_of_week="mon-fri", hour=17, minute=0),
        id="daily_sync_job",
        name="Đồng bộ dữ liệu giá lịch sử cuối ngày",
        replace_existing=True,
    )

    # Bắt đầu chạy Scheduler
    scheduler.start()
    print("🚀 [APScheduler] Đã kích hoạt Scheduler tự động chạy ngầm!")

    yield  # Ứng dụng FastAPI chạy ở đây

    # ---------------------------------------------------------
    # 2. TẮT SCHEDULER KHI FASTAPI SHUTDOWN
    # ---------------------------------------------------------
    scheduler.shutdown()
    print("🛑 [APScheduler] Đã dừng Scheduler thành công.")


# Khởi tạo FastAPI App với Lifespan manager
app = FastAPI(
    title="Nexus Trading Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# Cấu hình CORS để cho phép Frontend (React / Vue / Next.js) kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router, prefix="/api/v1")
app.include_router(stocks, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(portfolio_router, prefix="/api/v1")
app.include_router(portfolio_api_router, prefix="/api/v1")



@app.get("/")
def root():
    return {"message": "Nexus Backend Service is running smoothly!"}