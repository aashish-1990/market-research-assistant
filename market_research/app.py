# market_research/app.py
import os
import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple

import streamlit as st
from streamlit_chat import message

from market_research.config import AppConfig, ResearchParameters
from market_research.research import ResearchEngine
from market_research.dialog import DialogManager, DialogContext, DialogIntent
from market_research.voice import VoiceProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("market_research_app.log")
    ]
)
logger = logging.getLogger(__name__)

class MarketResearchApp:
    """Main application for the conversational market research assistant"""
    
    def __init__(self):
        """Initialize the application"""
        # Load configuration
        self.config = AppConfig.load_config()
        
        # Check for required API keys
        missing_keys = self.config.validate_keys()
        if missing_keys:
            st.error(f"Missing API keys: {', '.join(missing_keys)}")
            if "OPENAI_API_KEY" in missing_keys or "SERPER_API_KEY" in missing_keys:
                st.error("Critical API keys missing. The application may not function correctly.")
        
        # Initialize components
        self.research_engine = ResearchEngine(self.config)
        self.dialog_manager = DialogManager(self.config)
        
        # Initialize session state if needed
        if "context" not in st.session_state:
            st.session_state.context = self.dialog_manager.create_context()
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
            
        if "current_research" not in st.session_state:
            st.session_state.current_research = None
            
        if "research_in_progress" not in st.session_state:
            st.session_state.research_in_progress = False
            
        if "voice_enabled" not in st.session_state:
            st.session_state.voice_enabled = self.config.enable_voice
        
        # Initialize voice processor if enabled
        if self.config.enable_voice:
            try:
                self.voice_processor = VoiceProcessor(self.config)
                logger.info("Voice processor initialized")
            except Exception as e:
                logger.error(f"Error initializing voice processor: {str(e)}")
                st.session_state.voice_enabled = False
    
    def setup_ui(self):
        """Set up the Streamlit user interface"""
        st.set_page_config(
            page_title="AI Market Research Assistant",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Main layout
        self._setup_sidebar()
        self._setup_main_area()
    
    def _setup_sidebar(self):
        """Set up the sidebar with settings and options"""
        with st.sidebar:
            st.title("Market Research AI")
            st.subheader("Settings")
            
            # Voice toggle
            voice_enabled = st.toggle(
                "Enable Voice",
                value=st.session_state.voice_enabled,
                help="Toggle voice interaction on/off"
            )
            
            if voice_enabled != st.session_state.voice_enabled:
                st.session_state.voice_enabled = voice_enabled
                if voice_enabled:
                    try:
                        self.voice_processor = VoiceProcessor(self.config)
                        st.success("Voice mode enabled")
                    except Exception as e:
                        st.error(f"Failed to initialize voice: {str(e)}")
                        st.session_state.voice_enabled = False
            
            # Research depth
            st.session_state.research_depth = st.select_slider(
                "Research Depth",
                options=["Basic", "Standard", "Detailed"],
                value="Standard",
                help="Control the depth of research (affects processing time)"
            )
            
            # LLM Model selection (if using OpenAI)
            if self.config.llm_provider == "openai":
                model_options = ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
                selected_model = st.selectbox(
                    "AI Model",
                    options=model_options,
                    index=0,
                    help="Select the AI model (more advanced models provide better results but may be slower)"
                )
                
                if selected_model != self.config.llm_model:
                    self.config.llm_model = selected_model
                    # Reinitialize components with new model
                    self.research_engine = ResearchEngine(self.config)
                    self.dialog_manager = DialogManager(self.config)
            
            # Quick research topics
            st.subheader("Quick Research Topics")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("EV Market"):
                    self._handle_quick_topic("electric vehicle market trends")
                if st.button("AI Startups"):
                    self._handle_quick_topic("ai startup landscape 2024")
            
            with col2:
                if st.button("Health Tech"):
                    self._handle_quick_topic("health technology sector analysis")
                if st.button("Renewable Energy"):
                    self._handle_quick_topic("renewable energy market growth")
            
            # Session info
            st.subheader("Session Info")
            st.info(f"Session ID: {st.session_state.context.session_id[:8]}...")
            
            # Clear conversation
            if st.button("Clear Conversation", type="primary"):
                self._reset_conversation()
                st.rerun()
                
            # Display status
            if st.session_state.research_in_progress:
                st.warning("Research in progress...")
            
            st.divider()
            
            # About section
            st.caption("AI Market Research Assistant")
            st.caption("Powered by CrewAI + Streamlit")
    
    def _setup_main_area(self):
        """Set up the main chat area"""
        # Header
        st.title("AI Market Research Assistant")
        st.caption("Ask me about any market, industry, or company")
        
        # Chat container for messages
        chat_container = st.container()
        
        # Input area at the bottom
        input_container = st.container()
        
        # Display chat messages
        with chat_container:
            self._display_chat_messages()
        
        # Input area
        with input_container:
            col1, col2 = st.columns([6, 1])
            
            with col1:
                user_input = st.text_input(
                    "Your question",
                    key="user_input",
                    placeholder="Ask about any market, industry, or company...",
                    label_visibility="collapsed"
                )
            
            with col2:
                voice_button = st.button(
                    "🎤" if st.session_state.voice_enabled else "🔇",
                    key="voice_button",
                    help="Click to speak your query" if st.session_state.voice_enabled else "Voice input disabled"
                )
            
            # Process voice input
            if voice_button and st.session_state.voice_enabled:
                with st.spinner("Listening..."):
                    voice_input = self.voice_processor.listen()
                    if voice_input:
                        user_input = voice_input
                        st.session_state.user_input = voice_input
                        st.rerun()
            
            # Process text input
            if user_input:
                self._process_user_input(user_input)
    
    def _display_chat_messages(self):
        """Display chat messages in the UI"""
        if not st.session_state.messages:
            # Initial greeting if no messages
            initial_greeting = "Hello! I'm your AI Market Research Assistant. I can help with in-depth research on companies, markets, industries, and trends. What would you like to research today?"
            
            st.session_state.messages.append({"role": "assistant", "content": initial_greeting})
            st.session_state.context.add_message("assistant", initial_greeting)
        
        # Display all messages
        for i, msg in enumerate(st.session_state.messages):
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                message(content, is_user=True, key=f"msg_{i}")
            else:
                message(content, is_user=False, key=f"msg_{i}")
                
                # Add research results if available
                if "research_results" in msg:
                    with st.expander("📊 View Detailed Research"):
                        self._display_research_results(msg["research_results"])
    
    def _display_research_results(self, results):
        """Display structured research results"""
        # If results is a string (for back-compatibility)
        if isinstance(results, str):
            st.markdown(results)
            return
            
        # Otherwise, expect structured results
        if "sections" in results:
            # Display sections with tabs
            section_titles = list(results["sections"].keys())
            
            if section_titles:
                tabs = st.tabs([title.title() for title in section_titles])
                
                for i, section_title in enumerate(section_titles):
                    with tabs[i]:
                        section_content = results["sections"][section_title]
                        if isinstance(section_content, list):
                            for item in section_content:
                                st.markdown(f"• {item}")
                        else:
                            st.markdown(section_content)
        
        # Display any charts if available
        if "charts" in results and results["charts"]:
            st.subheader("Data Visualization")
            # Charts would be rendered here (placeholder for future implementation)
            st.info("Charts would be displayed here in a future version")
    
    def _process_user_input(self, user_input):
        """Process user input and generate a response"""
        # Clear the input box
        st.session_state.user_input = ""
        
        # Add user message to state
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Process message through dialog manager
        response, intent = self.dialog_manager.process_message(user_input, st.session_state.context)
        
        # Handle system commands
        if intent.type == "system_command" and intent.parameters.get("command") == "reset":
            self._reset_conversation()
            return
        
        # Add initial assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Determine if we need to conduct research
        if intent.type in ["research_request", "comparison_request"]:
            # Start a background research task
            st.session_state.research_in_progress = True
            st.rerun()
            
            # Create research parameters
            topic = intent.parameters.get("topic", user_input)
            params = ResearchParameters(
                query=topic,
                depth=st.session_state.research_depth.lower(),
                location="global",
                time_frame="2 years",
                input_type="company" if "company" in user_input.lower() else "topic"
            )
            
            # Run research in the main thread for now
            # In a production app, this would be a background task
            try:
                # Start research
                start_time = time.time()
                research_results = self.research_engine.conduct_research(params)
                elapsed_time = time.time() - start_time
                
                # Process results
                final_report = research_results.get("final_report", "")
                sections = self.research_engine.extract_sections(final_report)
                
                # Update the last assistant message with research results
                st.session_state.messages[-1]["research_results"] = {
                    "summary": research_results.get("result_summary", ""),
                    "sections": sections,
                    "metadata": {
                        "research_time": f"{elapsed_time:.1f} seconds",
                        "depth": params.depth,
                        "topic": params.query
                    }
                }
                
                # Update context with new topic
                st.session_state.context.current_topic = topic
                st.session_state.context.current_research_id = research_results.get("metadata", {}).get("research_id")
                
                # Voice response if enabled
                if st.session_state.voice_enabled:
                    # Extract a summary for voice response
                    if "executive summary" in sections:
                        voice_summary = "\n".join(sections["executive summary"][:2])
                    else:
                        voice_summary = "\n".join(list(sections.values())[0][:2]) if sections else final_report[:500]
                    
                    self.voice_processor.speak(f"Here's what I found about {topic}: {voice_summary}")
                
            except Exception as e:
                logger.error(f"Error conducting research: {str(e)}", exc_info=True)
                error_message = f"I encountered an error while researching {topic}: {str(e)}"
                
                # Add error message to chat
                st.session_state.messages.append({"role": "assistant", "content": error_message})
            finally:
                st.session_state.research_in_progress = False
                
        # Voice response for non-research intents
        elif st.session_state.voice_enabled:
            self.voice_processor.speak(response)
    
    def _handle_quick_topic(self, topic):
        """Handle selection of a quick research topic"""
        self._process_user_input(f"Research {topic}")
    
    def _reset_conversation(self):
        """Reset the conversation state"""
        # Keep the session ID
        session_id = st.session_state.context.session_id
        
        # Create new context with same session ID
        st.session_state.context = self.dialog_manager.create_context(session_id)
        st.session_state.messages = []
        st.session_state.current_research = None
        st.session_state.research_in_progress = False
        
        logger.info(f"Conversation reset for session {session_id}")

def main():
    """Main entry point for the application"""
    try:
        app = MarketResearchApp()
        app.setup_ui()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        logger.error(f"Application error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
