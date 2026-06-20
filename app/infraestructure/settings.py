from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    orchestrator_url: str

    class Config:
        env_file = ".env"


settings = Settings()
