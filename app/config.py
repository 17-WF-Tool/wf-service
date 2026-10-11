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
    WF_MARKET_ASSETS_URL: str = "https://warframe.market/static/assets/"

    # 物品目錄：定期檢查版本的間隔，以及查不到物品時觸發更新的冷卻時間（秒）
    CATALOG_REFRESH_INTERVAL: float = 3600
    CATALOG_MISS_REFRESH_COOLDOWN: float = 300

    # 預設查詢的使用者名稱（若前端呼叫沒帶參數時使用）
    DEFAULT_WF_USERNAME: str = ""


settings = Settings()
