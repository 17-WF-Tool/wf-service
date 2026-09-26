from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    APP_ENV: str = "development"
    API_PORT: int = 8000
    ALLOWED_ORIGINS: tuple = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    WF_MARKET_API_URL: str = "https://api.warframe.market/v2"

    # 預設查詢的使用者名稱（若前端呼叫沒帶參數時使用）
    DEFAULT_WF_USERNAME: str = ""


settings = Settings()
