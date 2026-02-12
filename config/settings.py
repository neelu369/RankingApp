"""
Configuration management for the Ranking App
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys
    replicate_api_key: str = os.getenv("REPLICATE_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # MongoDB
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb+srv://rankinguser:Hq2otsnjOJTO8Ezj@instantai.sff1nma.mongodb.net/?appName=instantai")
    mongodb_db_name: str = os.getenv("MONGODB_DB_NAME", "rankingdb")
    
    # Crawler
    crawl4ai_max_pages: int = int(os.getenv("CRAWL4AI_MAX_PAGES", "50"))
    crawl4ai_timeout: int = int(os.getenv("CRAWL4AI_TIMEOUT", "30"))
    
    # LLM
    default_llm_model: str = os.getenv("DEFAULT_LLM_MODEL", "meta/meta-llama-3-70b-instruct")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    
    # Application
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()