from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    soroban_rpc_url: str = "https://soroban-testnet.stellar.org"
    network_passphrase: str = "Test SDF Network ; September 2015"
    contract_id: str = ""
    ai_agent_url: str = "http://localhost:8001"
    responder_secret_key: str = ""  # set via .env; empty means submission is disabled
    environment: str = "development"
    api_key: str = ""  # set via .env; empty means API key auth is disabled

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
