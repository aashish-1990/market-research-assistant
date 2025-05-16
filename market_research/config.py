# market_research/config.py
import os
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("market_research.log")
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ResearchParameters(BaseModel):
    """Research parameters for market research queries"""
    query: str = Field(..., description="Main topic or company to research")
    depth: str = Field("detailed", description="Research depth (basic, standard, detailed)")
    location: str = Field("global", description="Geographical focus (e.g., global, US, Europe)")
    time_frame: str = Field("2 years", description="Time period to consider (e.g., 1 year, 5 years)")
    input_type: str = Field("topic", description="Type of input (topic, company)")
    
    @classmethod
    def from_user_input(cls, query: str) -> 'ResearchParameters':
        """Create parameters from user input with defaults"""
        return cls(
            query=query,
            depth="detailed",
            location="global",
            time_frame="2 years",
            input_type="topic" if not query.lower().endswith(" company") else "company"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.dict()
    
class AppConfig(BaseModel):
    """Application configuration"""
    # API Keys
    openai_api_key: str = Field(os.getenv("OPENAI_API_KEY", ""), description="OpenAI API key")
    serper_api_key: str = Field(os.getenv("SERPER_API_KEY", ""), description="Serper API key")
    elevenlabs_api_key: str = Field(os.getenv("ELEVENLABS_API_KEY", ""), description="ElevenLabs API key")
    
    # LLM Configuration
    llm_provider: str = Field(os.getenv("LLM_PROVIDER", "openai"), description="LLM provider (openai, anthropic)")
    llm_model: str = Field(os.getenv("LLM_MODEL", "gpt-4o"), description="LLM model name")
    temperature: float = Field(float(os.getenv("LLM_TEMPERATURE", "0.7")), description="LLM temperature")
    
    # Voice Configuration
    enable_voice: bool = Field(os.getenv("ENABLE_VOICE", "False").lower() == "true", description="Enable voice features")
    tts_provider: str = Field(os.getenv("TTS_PROVIDER", "gtts"), description="TTS provider (gtts, elevenlabs)")
    stt_provider: str = Field(os.getenv("STT_PROVIDER", "google"), description="STT provider (google, whisper)")
    
    # Research Configuration
    process_type: str = Field(os.getenv("PROCESS_TYPE", "sequential"), description="CrewAI process type (sequential, hierarchical)")
    max_sources: int = Field(int(os.getenv("MAX_SOURCES", "10")), description="Maximum number of sources to use")
    max_scrape_depth: int = Field(int(os.getenv("MAX_SCRAPE_DEPTH", "3")), description="Maximum scraping depth")
    
    # Application Configuration
    verbose: bool = Field(os.getenv("VERBOSE", "True").lower() == "true", description="Verbose output")
    debug: bool = Field(os.getenv("DEBUG", "False").lower() == "true", description="Debug mode")
    data_dir: str = Field(os.getenv("DATA_DIR", "./data"), description="Data directory")
    cache_enabled: bool = Field(os.getenv("CACHE_ENABLED", "True").lower() == "true", description="Enable caching")
    
    def validate_keys(self) -> List[str]:
        """Validate required API keys and return missing keys"""
        missing_keys = []
        
        if not self.openai_api_key:
            missing_keys.append("OPENAI_API_KEY")
        if not self.serper_api_key:
            missing_keys.append("SERPER_API_KEY")
        if self.enable_voice and self.tts_provider == "elevenlabs" and not self.elevenlabs_api_key:
            missing_keys.append("ELEVENLABS_API_KEY")
            
        return missing_keys
    
    @classmethod
    def load_config(cls) -> 'AppConfig':
        """Load configuration from environment variables"""
        config = cls()
        missing_keys = config.validate_keys()
        
        if missing_keys:
            logger.warning(f"Missing API keys: {', '.join(missing_keys)}")
            if "OPENAI_API_KEY" in missing_keys or "SERPER_API_KEY" in missing_keys:
                logger.error("Critical API keys missing. The application may not function correctly.")
                
        return config
