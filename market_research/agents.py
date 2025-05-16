# market_research/agents.py
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache

from crewai import Agent
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, FileReadTool, FileWriteTool
from langchain.tools import tool

from market_research.config import AppConfig

logger = logging.getLogger(__name__)

class CustomScrapeWebsiteTool(ScrapeWebsiteTool):
    """Enhanced scraping tool with better error handling and depth control"""
    
    def __init__(self, max_depth: int = 3):
        super().__init__()
        self.max_depth = max_depth
        
    def _run(self, url: str) -> str:
        """Run the tool with error handling and depth control"""
        try:
            logger.info(f"Scraping website: {url}")
            result = super()._run(url)
            
            # Limit result size to avoid token issues
            if len(result) > 8000:
                logger.info(f"Truncating long scraping result from {len(result)} chars to 8000")
                result = result[:8000] + "...[Content truncated due to length]"
            
            return result
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return f"Error scraping {url}: {str(e)}"

class CustomSerperDevTool(SerperDevTool):
    """Enhanced search tool with better error handling and result formatting"""
    
    def _run(self, query: str) -> str:
        """Run the tool with error handling"""
        try:
            logger.info(f"Searching: {query}")
            result = super()._run(query)
            return result
        except Exception as e:
            logger.error(f"Error searching for '{query}': {str(e)}")
            return f"Error searching for '{query}': {str(e)}. Please try with a different query."

class CacheTool:
    """Tool for caching and retrieving research results"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
    @tool("save_to_cache")
    def save_to_cache(self, key: str, data: str) -> str:
        """Save data to cache with the given key"""
        try:
            sanitized_key = key.replace(" ", "_").replace("/", "_").lower()
            file_path = os.path.join(self.data_dir, f"{sanitized_key}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(data)
            return f"Successfully saved data with key '{key}'"
        except Exception as e:
            logger.error(f"Error saving to cache: {str(e)}")
            return f"Error saving to cache: {str(e)}"
    
    @tool("load_from_cache")
    def load_from_cache(self, key: str) -> str:
        """Load data from cache with the given key"""
        try:
            sanitized_key = key.replace(" ", "_").replace("/", "_").lower()
            file_path = os.path.join(self.data_dir, f"{sanitized_key}.txt")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            return "No data found in cache for this key"
        except Exception as e:
            logger.error(f"Error loading from cache: {str(e)}")
            return f"Error loading from cache: {str(e)}"

class ResearchAgents:
    """Factory for creating research agents"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.llm = self._initialize_llm()
        self.tools = self._initialize_tools()
        
    def _initialize_llm(self):
        """Initialize the language model based on configuration"""
        try:
            if self.config.llm_provider == "openai":
                return ChatOpenAI(
                    api_key=self.config.openai_api_key,
                    model=self.config.llm_model,
                    temperature=self.config.temperature
                )
            elif self.config.llm_provider == "anthropic":
                return ChatAnthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                    model=self.config.llm_model,
                    temperature=self.config.temperature
                )
            else:
                logger.error(f"Unsupported LLM provider: {self.config.llm_provider}")
                raise ValueError(f"Unsupported LLM provider: {self.config.llm_provider}")
        except Exception as e:
            logger.error(f"Error initializing LLM: {str(e)}")
            raise RuntimeError(f"Failed to initialize LLM: {str(e)}")
    
    def _initialize_tools(self) -> Dict[str, Any]:
        """Initialize all tools used by agents"""
        try:
            search_tool = CustomSerperDevTool(api_key=self.config.serper_api_key)
            scrape_tool = CustomScrapeWebsiteTool(max_depth=self.config.max_scrape_depth)
            cache_tool = CacheTool(data_dir=self.config.data_dir)
            file_read_tool = FileReadTool()
            file_write_tool = FileWriteTool()
            
            return {
                "search": search_tool,
                "scrape": scrape_tool,
                "cache": cache_tool,
                "file_read": file_read_tool,
                "file_write": file_write_tool
            }
        except Exception as e:
            logger.error(f"Error initializing tools: {str(e)}")
            raise RuntimeError(f"Failed to initialize tools: {str(e)}")
            
    def get_dialog_agent(self) -> Agent:
        """Create a dialog management agent"""
        return Agent(
            role="Conversation Manager",
            goal="Maintain natural conversation flow and extract research parameters from user queries",
            backstory="An empathetic conversationalist skilled at understanding user needs and creating engaging dialog",
            tools=[],
            llm=self.llm,
            verbose=self.config.verbose,
            allow_delegation=False,
            memory=True
        )
    
    def get_researcher_agent(self) -> Agent:
        """Create a researcher agent"""
        return Agent(
            role="Research Specialist",
            goal="Find comprehensive, accurate information on any topic from multiple reliable sources",
            backstory="A meticulous researcher with expertise in evaluating source credibility and finding deep insights",
            tools=[
                self.tools["search"],
                self.tools["scrape"],
                self.tools["cache"],
                self.tools["file_write"]
            ],
            llm=self.llm,
            verbose=self.config.verbose,
            allow_delegation=True,
            memory=True
        )
    
    def get_analyst_agent(self) -> Agent:
        """Create an analyst agent"""
        return Agent(
            role="Data Analyst",
            goal="Analyze research findings to identify key trends, comparisons, and insights",
            backstory="An analytical expert who excels at finding patterns and meaningful connections in complex data",
            tools=[
                self.tools["cache"],
                self.tools["file_read"]
            ],
            llm=self.llm,
            verbose=self.config.verbose,
            allow_delegation=True,
            memory=True
        )
    
    def get_writer_agent(self) -> Agent:
        """Create a content writer agent"""
        return Agent(
            role="Content Strategist",
            goal="Transform research and analysis into clear, engaging, and actionable content",
            backstory="A talented communicator who makes complex information accessible and compelling for different audiences",
            tools=[
                self.tools["cache"], 
                self.tools["file_read"]
            ],
            llm=self.llm,
            verbose=self.config.verbose,
            allow_delegation=False,
            memory=True
        )
    
    def get_verifier_agent(self) -> Agent:
        """Create a verification agent"""
        return Agent(
            role="Fact Checker",
            goal="Verify the accuracy and completeness of research findings with multiple sources",
            backstory="A meticulous verifier who ensures information is accurate, balanced, and properly sourced",
            tools=[
                self.tools["search"],
                self.tools["scrape"],
                self.tools["cache"]
            ],
            llm=self.llm,
            verbose=self.config.verbose,
            allow_delegation=True,
            memory=True
        )
    
    def get_all_agents(self) -> Dict[str, Agent]:
        """Get all agents in a dictionary"""
        return {
            "dialog": self.get_dialog_agent(),
            "researcher": self.get_researcher_agent(),
            "analyst": self.get_analyst_agent(),
            "writer": self.get_writer_agent(),
            "verifier": self.get_verifier_agent()
        }
