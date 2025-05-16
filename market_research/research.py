# market_research/research.py
import os
import json
import uuid
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from crewai import Task, Crew, Process
from langchain.prompts import PromptTemplate

from market_research.config import AppConfig, ResearchParameters
from market_research.agents import ResearchAgents

logger = logging.getLogger(__name__)

class ResearchEngine:
    """Core research engine for market research"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.agents = ResearchAgents(config)
        
    def create_research_tasks(self, params: ResearchParameters) -> List[Task]:
        """Create research tasks based on parameters"""
        logger.info(f"Creating research tasks for query: {params.query}")
        
        agents = self.agents.get_all_agents()
        task_id = str(uuid.uuid4())[:8]
        cache_key = f"research_{params.query[:20]}_{task_id}"
        
        # Parameter extraction task
        parameter_extraction_task = Task(
            description=f"""
            Extract and enhance research parameters from this original request:
            Query: {params.query}
            Depth: {params.depth}
            Location: {params.location}
            Time Frame: {params.time_frame}
            Input Type: {params.input_type}
            
            Your job is to enhance these parameters by:
            1. Identifying the main topic or company more precisely
            2. Determining specific aspects that should be researched
            3. Identifying relevant industries, competitors, or related areas
            4. Suggesting specific data sources that might be valuable
            5. Proposing a search strategy with specific keywords
            
            Return your enhanced parameters in a structured JSON format that includes:
            - refined_query: A more precise version of the original query
            - aspects: A list of specific aspects to research
            - keywords: A list of search keywords to use
            - sources: Suggested types of sources to prioritize
            - search_strategy: Brief description of the recommended approach
            """,
            expected_output=f"Enhanced research parameters in JSON format for '{params.query}'",
            agent=agents["dialog"]
        )
        
        # Main research task
        research_task = Task(
            description=f"""
            Conduct comprehensive research on {'the company' if params.input_type == 'company' else 'the topic'}: "{params.query}"
            with a {params.depth} focus in {params.location} over the past {params.time_frame}.
            
            Use the enhanced parameters from the previous task to guide your research.
            
            Your research should include:
            1. {'Company background, history, and main products/services' if params.input_type == 'company' else 'Topic background and key concepts'}
            2. {'Market position, competitors, and market share' if params.input_type == 'company' else 'Current trends and developments'}
            3. {'Financial performance and funding history' if params.input_type == 'company' else 'Key players and organizations in this space'}
            4. {'SWOT analysis (strengths, weaknesses, opportunities, threats)' if params.input_type == 'company' else 'Market size and growth projections'}
            5. {'Recent news, developments, and strategic initiatives' if params.input_type == 'company' else 'Challenges and opportunities'}
            6. {'Future outlook and growth potential' if params.input_type == 'company' else 'Future predictions and emerging trends'}
            
            Use multiple sources to ensure comprehensive coverage. Search for information first, then 
            scrape specific websites for deeper insights. For each finding, note the source.
            
            Save your raw research findings using the cache tool with key: "{cache_key}_raw"
            """,
            expected_output=f"Comprehensive raw research on {params.query}",
            agent=agents["researcher"],
            context=[parameter_extraction_task]
        )
        
        # Analysis task
        analysis_task = Task(
            description=f"""
            Analyze the raw research findings on {params.query} that were saved with the key "{cache_key}_raw".
            
            Your analysis should:
            1. Identify key trends, patterns, and insights
            2. Evaluate the credibility and consistency of different sources
            3. Highlight any contradictions or gaps in the information
            4. Draw connections between different aspects of the research
            5. Organize the information into logical categories
            
            For {'company' if params.input_type == 'company' else 'topic'} research, focus on:
            {'- Business model and revenue streams\n- Competitive advantage and differentiators\n- Market positioning and strategy\n- Financial health and performance\n- Growth vectors and challenges' 
            if params.input_type == 'company' else 
            '- Current state and major developments\n- Key influencers and thought leaders\n- Regional differences and patterns\n- Historical context and evolution\n- Future trajectory and potential disruptions'}
            
            Save your analysis using the cache tool with key: "{cache_key}_analysis"
            """,
            expected_output=f"Structured analysis of research on {params.query}",
            agent=agents["analyst"],
            context=[research_task]
        )
        
        # Verification task
        verification_task = Task(
            description=f"""
            Verify the accuracy and completeness of the research and analysis on {params.query} 
            that were saved with the keys "{cache_key}_raw" and "{cache_key}_analysis".
            
            Your verification should:
            1. Check if all the required aspects were covered
            2. Verify key facts from multiple sources when possible
            3. Identify any potentially outdated or incorrect information
            4. Look for potential biases in the sources or analysis
            5. Fill in any important gaps with additional research
            
            If you find discrepancies or missing information, conduct additional search and research 
            to correct or complete the information.
            
            Save your verification results using the cache tool with key: "{cache_key}_verified"
            """,
            expected_output=f"Verified research findings on {params.query}",
            agent=agents["verifier"],
            context=[research_task, analysis_task]
        )
        
        # Content creation task
        content_task = Task(
            description=f"""
            Create a comprehensive, well-structured research report on {params.query} based on the 
            verified research and analysis saved with keys "{cache_key}_raw", "{cache_key}_analysis", and "{cache_key}_verified".
            
            Your report should:
            1. Begin with an executive summary that highlights key findings
            2. Be organized in clear sections with descriptive headings
            3. Include relevant data, statistics, and trends
            4. Be written in a clear, engaging style suitable for both voice and text presentation
            5. Conclude with actionable insights or recommendations
            
            Format requirements:
            - Use markdown formatting for structure (headings, bullet points, etc.)
            - Keep paragraphs relatively short for readability
            - Use bold text for key points
            - Include a structured table of contents
            - Organize information in a logical flow
            
            Save your final report using the cache tool with key: "{cache_key}_final"
            """,
            expected_output=f"Comprehensive research report on {params.query}",
            agent=agents["writer"],
            context=[research_task, analysis_task, verification_task]
        )
        
        return [parameter_extraction_task, research_task, analysis_task, verification_task, content_task]
    
    def conduct_research(self, params: ResearchParameters) -> Dict[str, Any]:
        """Run the full research process and return results"""
        start_time = time.time()
        logger.info(f"Starting research process for: {params.query}")
        
        try:
            # Create tasks
            tasks = self.create_research_tasks(params)
            
            # Create the research crew
            agents_list = list(self.agents.get_all_agents().values())
            
            crew = Crew(
                agents=agents_list,
                tasks=tasks,
                verbose=self.config.verbose,
                process=Process.sequential if self.config.process_type == "sequential" else Process.hierarchical
            )
            
            # Run the research
            task_id = str(uuid.uuid4())[:8]
            cache_key = f"research_{params.query[:20]}_{task_id}"
            result = crew.kickoff()
            
            # Load results from cache
            try:
                raw_data = self.agents.tools["cache"].load_from_cache(f"{cache_key}_raw")
                analysis = self.agents.tools["cache"].load_from_cache(f"{cache_key}_analysis")
                verified = self.agents.tools["cache"].load_from_cache(f"{cache_key}_verified")
                final = self.agents.tools["cache"].load_from_cache(f"{cache_key}_final")
            except Exception as e:
                logger.warning(f"Error loading results from cache: {str(e)}. Using result.raw instead.")
                raw_data = result.raw
                analysis = result.raw
                verified = result.raw
                final = result.raw
            
            # Format results
            elapsed_time = time.time() - start_time
            research_results = {
                "query": params.query,
                "parameters": params.to_dict(),
                "raw_data": raw_data,
                "analysis": analysis,
                "verified": verified,
                "final_report": final,
                "result_summary": result.raw,
                "metadata": {
                    "research_id": task_id,
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_time": elapsed_time,
                    "model": self.config.llm_model
                }
            }
            
            # Save the full results
            results_path = os.path.join(self.config.data_dir, f"research_results_{task_id}.json")
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(research_results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Research completed in {elapsed_time:.2f} seconds. Results saved to {results_path}")
            
            return research_results
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error conducting research: {str(e)}", exc_info=True)
            
            # Return error response
            return {
                "query": params.query,
                "parameters": params.to_dict(),
                "error": str(e),
                "metadata": {
                    "research_id": str(uuid.uuid4())[:8],
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_time": elapsed_time,
                    "status": "error"
                }
            }
    
    def extract_sections(self, report: str) -> Dict[str, List[str]]:
        """Extract structured sections from the research report"""
        sections = {}
        current_section = "overview"
        current_content = []
        
        for line in report.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Check for section headers
            if line.startswith('# '):
                # Skip the title
                continue
            elif line.startswith('## '):
                # Save previous section
                if current_content:
                    sections[current_section] = current_content
                    
                # Start new section
                current_section = line.replace('## ', '').lower()
                current_content = []
            elif line.startswith('### '):
                # For subsections, we'll treat them as part of the current section
                # but add them with their header
                subsection = line.replace('### ', '')
                current_content.append(f"**{subsection}**")
            else:
                # Add to current section
                current_content.append(line)
        
        # Add the last section
        if current_content:
            sections[current_section] = current_content
            
        return sections
