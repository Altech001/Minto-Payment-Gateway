from pydantic_settings import BaseSettings, SettingsConfigDict

#Marz Pay Settings
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    MARZ_API_BASE_URL: str = "https://wallet.wearemarz.com/api/v1"
    MARZ_API_KEY: str = "bWFyel9BcXFTQmprQXhGUFhQakJCOlJnc0UwQTBvQkFpQUlpd21qNmFwTVhDaUhuYzJYY2Ru"



settings = Settings()