import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Nexus Stock Analysis & Portfolio API"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:admin123456@localhost:5432/nexus_db",
    )
    print(DATABASE_URL)
    TWELVE_DATA_API_KEY: str = os.getenv("TWELVE_DATA_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")


settings = Settings()