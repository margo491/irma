from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/irma"
    bonus_earn_rate: float = 0.05
    bonus_max_spend_rate: float = 0.20
    max_token: str = ""
    token_bot_max: str = ""
    admin_max_user_id: str = ""
    admin_email: str = ""
    admin_password: str = ""
    news_publish_delay_minutes: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
