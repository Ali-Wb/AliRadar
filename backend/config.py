from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AliRadar"
    VERSION: str = "1.0.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8765
    DB_PATH: str = "aliradar.db"
    OUI_PATH: str = "../data/oui.csv"
    SCAN_INTERVAL_SECONDS: float = 3.0
    CLASSIC_INQUIRY_DURATION: int = 8
    RSSI_PATH_LOSS_EXPONENT: float = 2.5
    TX_POWER_DEFAULT: int = -59
    RSSI_MINIMUM: int = -100
    MAX_DEVICE_AGE_MINUTES: int = 10
    ALERT_LINGER_MINUTES: int = 10
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
