from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/irma"
    bonus_earn_rate: float = 0.05
    bonus_max_spend_rate: float = 0.20
    max_token: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
