"""
Config files are for validating environment variables and setting default values for them.
 They are not for storing secrets, as they will be committed to version control. 
 Use a .env file for secrets instead.

"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):

    #LLM_CONFiguration
    groq_api_key: str
    primary_model: str = "llama-3.3-70b-versatile"
    secondary_model: str = "llama-3.1-8b-instant"

    #langsmith configuration
    langchain_api_key: str
    langchain_project: str = "production-api"
    langchain_tracing_v2: bool = True

    #application
    app_env: str = "development"
    log_level: str = "INFO"
    rate_limit: str = "20/minute"
    cache_ttl_seconds: int = 300
    max_retries: int = 3

    model_config = {"env_file": ".env", "extra": "ignore"}

        
    def configure_langsmith(self):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = self.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = self.langchain_project

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance once loaded reused everywhere"""
    settings = Settings()
    settings.configure_langsmith()
    return Settings()



# # Paste this temporarily at the bottom of config.py and run it directly
# # python -m app.config  (or however you run your app)

# if __name__ == "__main__":
#     settings = get_settings()
    
#     print("=== Pydantic values ===")
#     print(f"langchain_api_key: {settings.langchain_api_key[:8]}...")  # partial for safety
#     print(f"langchain_project: {settings.langchain_project}")
#     print(f"langchain_tracing_v2: {settings.langchain_tracing_v2}")
    
#     print("\n=== os.environ after configure_langsmith ===")
#     print(f"LANGCHAIN_API_KEY: {os.environ.get('LANGCHAIN_API_KEY', 'NOT SET')[:8]}...")
#     print(f"LANGCHAIN_PROJECT: {os.environ.get('LANGCHAIN_PROJECT', 'NOT SET')}")
#     print(f"LANGCHAIN_TRACING_V2: {os.environ.get('LANGCHAIN_TRACING_V2', 'NOT SET')}")