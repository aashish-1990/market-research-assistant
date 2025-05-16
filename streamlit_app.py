import streamlit as st
import openai
import time
import json
import logging
import traceback
from datetime import datetime

# Configure logging to be more verbose
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Function to show debug info on screen
def show_debug(message):
    with st.sidebar.expander("Debug Info", expanded=True):
        st.write(message)

# Debug info container at the bottom
if "debug_info" not in st.session_state:
    st.session_state.debug_info = []

# Add API Key Debug check
try:
    # Display check for API key from secrets
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "Invalid key format"
        st.session_state.debug_info.append(f"API Key from secrets: {masked_key}")
        openai.api_key = api_key
        st.session_state.debug_info.append("OpenAI API key set from secrets")
    else:
        st.session_state.debug_info.append("API Key not found in secrets")
        # Fallback to direct input if needed
        api_key = st.sidebar.text_input("OpenAI API Key (Fallback)", type="password")
        if api_key:
            openai.api_key = api_key
            st.session_state.debug_info.append("OpenAI API key set from input")
except Exception as e:
    error_msg = f"Error accessing API key: {str(e)}"
    st.session_state.debug_info.append(error_msg)
    st.error(error_msg)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.debug_info.append("Initialized messages state")

if "research_in_progress" not in st.session_state:
    st.session_state.research_in_progress = False
    st.session_state.debug_info.append("Initialized research_in_progress state")

if "current_topic" not in st.session_state:
    st.session_state.current_topic = None
    st.session_state.debug_info.append("Initialized current_topic state")

# App title and description
st.title("AI Market Research Assistant")
st.caption("Ask me about any market, industry, or company")

# Sidebar
with st.sidebar:
    st.title("Market Research AI")
    st.subheader("Settings")
    
    # Research depth
    research_depth = st.select_slider(
        "Research Depth",
        options=["Basic", "Standard", "Detailed"],
        value="Standard",
        help="Control the depth of research (affects processing time)"
    )
    st.session_state.debug_info.append(f"Research depth set to: {research_depth}")
    
    # Geographic focus
    geographic_options = [
        "Global", "North America", "Europe", "Asia-Pacific", 
        "Latin America", "Middle East & Africa", "United States", 
        "China", "India", "European Union"
    ]
    geographic_focus = st.selectbox(
        "Geographic Focus",
        options=geographic_options,
        index=0,
        help="Select the geographic region to focus research on"
    )
    st.session_state.debug_info.append(f"Geographic focus set to: {geographic_focus}")
    
    # Time period
    time_period_options = [
        "Current (Last 6 months)", 
        "Recent (Last 1-2 years)", 
        "Medium-term (Last 3-5 years)",
        "Long-term (Last decade)"
    ]
    time_period = st.selectbox(
        "Time Period",
        options=time_period_options,
        index=1,
        help="Select the time period to focus research on"
    )
    st.session_state.debug_info.append(f"Time period set to: {time_period}")
    
    # Quick research topics
    st.subheader("Quick Research Topics")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("EV Market"):
            st.session_state.messages.append({"role": "user", "content": "Research electric vehicle market trends"})
            st.session_state.debug_info.append("EV Market button clicked")
            st.rerun()
        
        if st.button("AI Startups"):
            st.session_state.messages.append({"role": "user", "content": "Research AI startup landscape 2024"})
            st.session_state.debug_info.append("AI Startups button clicked")
            st.rerun()
    
    with col2:
        if st.button("Health Tech"):
            st.session_state.messages.append({"role": "user", "content": "Research health technology sector"})
            st.session_state.debug_info.append("Health Tech button clicked")
            st.rerun()
        
        if st.button("Renewable Energy"):
            st.session_state.messages.append({"role": "user", "content": "Research renewable energy market"})
            st.session_state.debug_info.append("Renewable Energy button clicked")
            st.rerun()
    
    # Clear conversation
    if st.button("Clear Conversation", type="primary"):
        st.session_state.messages = []
        st.session_state.current_topic = None
        st.session_state.debug_info.append("Conversation cleared")
        st.rerun()
    
    # Show API status
    if openai.api_key:
        st.success("✅ OpenAI API key configured")
    else:
        st.error("❌ OpenAI API key missing")
    
    # Debug expander
    with st.expander("Debug Information", expanded=False):
        st.write("Debug Messages:")
        for msg in st.session_state.debug_info[-10:]:  # Show last 10 debug messages
            st.text(msg)
        if st.button("Clear Debug Info"):
            st.session_state.debug_info = []
            st.rerun()

# Function to conduct market research
def conduct_research(topic, depth="standard", region="Global", time_frame="Recent (Last 1-2 years)"):
    try:
        st.session_state.debug_info.append(f"Starting research on: {topic}")
        st.session_state.research_in_progress = True
        st.session_state.debug_info.append("Set research_in_progress to True")
        
        # Check API key
        if not openai.api_key:
            st.session_state.debug_info.append("Error: OpenAI API key not configured")
            return "Error: OpenAI API key is not configured. Please check the app settings."
        
        # Create system message for detailed research
        system_message = f"""You are an expert market research assistant. 
        Conduct detailed research on: {topic}.
        
        Research parameters:
        - Depth: {depth}
        - Geographic focus: {region}
        - Time period: {time_frame}
        
        Your response should include:
        1. Market overview with specific focus on {region}
        2. Key players and companies in this market
        3. Market size and growth trends over {time_frame}
        4. Future outlook and predictions
        5. Challenges and opportunities specific to {region}
        6. Regulatory environment if relevant
        
        Format your response using markdown with clear sections and bullet points.
        Include data and statistics where relevant.
        Be sure to frame all analysis within the {time_frame} time period.
        """
        
        # Log the system message
        st.session_state.debug_info.append(f"System message created, length: {len(system_message)}")
        
        # Get current timestamp for research metadata
        timestamp = datetime.now().isoformat()
        st.session_state.debug_info.append(f"Timestamp: {timestamp}")
        
        # Display a progress message
        st.session_state.debug_info.append("About to call OpenAI API")
        
        # Call OpenAI API with timeout and spinner
        with st.spinner(f"Researching {topic} for {region} over {time_frame}... This may take up to 30 seconds for detailed analysis"):
            st.session_state.debug_info.append("Making API call to OpenAI...")
            
            # Logging the request
            user_content = f"Research this topic in detail: {topic} in {region} over {time_frame}"
            st.session_state.debug_info.append(f"User content length: {len(user_content)}")
            
            try:
                # Attempt API call
                st.session_state.debug_info.append("Starting OpenAI API call")
                start_time = time.time()
                
                # Call OpenAI API
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.7,
                )
                
                elapsed_time = time.time() - start_time
                st.session_state.debug_info.append(f"OpenAI API call completed in {elapsed_time:.2f} seconds")
                
                # Extract research result
                research_result = response.choices[0].message.content
                st.session_state.debug_info.append(f"Research result received, length: {len(research_result)}")
                
                # Extract sections for detailed view
                st.session_state.debug_info.append("Extracting sections from result")
                sections = extract_sections(research_result)
                st.session_state.debug_info.append(f"Extracted {len(sections)} sections")
                
                # Create final result with metadata
                result = {
                    "content": research_result,
                    "sections": sections,
                    "metadata": {
                        "topic": topic,
                        "depth": depth,
                        "region": region,
                        "time_frame": time_frame,
                        "timestamp": timestamp,
                        "processing_time": f"{elapsed_time:.2f} seconds"
                    }
                }
                
                st.session_state.debug_info.append("Research completed successfully")
                return result
                
            except Exception as api_error:
                st.session_state.debug_info.append(f"OpenAI API error: {str(api_error)}")
                st.session_state.debug_info.append(traceback.format_exc())
                error_message = f"Error calling OpenAI API: {str(api_error)}"
                st.error(error_message)
                return error_message
    
    except Exception as e:
        st.session_state.debug_info.append(f"General research error: {str(e)}")
        st.session_state.debug_info.append(traceback.format_exc())
        error_message = f"I encountered an error while researching {topic}: {str(e)}"
        st.error(error_message)  # Show error in UI
        return error_message
    
    finally:
        st.session_state.research_in_progress = False
        st.session_state.debug_info.append("Set research_in_progress to False")

# Function to extract sections from research result
def extract_sections(text):
    st.session_state.debug_info.append("Starting section extraction")
    sections = {}
    current_section = "overview"
    current_content = []
    
    for line in text.split('\n'):
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
            st.session_state.debug_info.append(f"Found section: {current_section}")
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
        
    st.session_state.debug_info.append(f"Completed section extraction: {len(sections)} sections found")
    return sections

# Display chat messages
st.session_state.debug_info.append(f"Displaying {len(st.session_state.messages)} messages")
for i, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    content = msg["content"]
    
    if role == "user":
        st.chat_message("user").write(content)
    else:
        st.chat_message("assistant").write(content)
        
        # Add research results if available
        if "research_results" in msg:
            with st.expander("📊 View Detailed Research"):
                result = msg["research_results"]
                
                # Display metadata
                st.caption(f"Research focus: {result.get('metadata', {}).get('region', 'Global')} | Time period: {result.get('metadata', {}).get('time_frame', 'Recent')}")
                
                # Display sections
                if "sections" in result:
                    section_titles = list(result["sections"].keys())
                    
                    if section_titles:
                        tabs = st.tabs([title.title() for title in section_titles])
                        
                        for i, section_title in enumerate(section_titles):
                            with tabs[i]:
                                section_content = result["sections"][section_title]
                                for item in section_content:
                                    st.markdown(f"• {item}")

# User input and processing
st.session_state.debug_info.append("Setting up user input processing")
if prompt := st.chat_input("Ask about any market or industry..."):
    st.session_state.debug_info.append(f"User input received: {prompt[:50]}...")
    
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.debug_info.append("Added user message to state")
    
    # Check if this is a research request
    is_research_request = any(keyword in prompt.lower() for keyword in 
                             ["research", "analyze", "tell me about", "what is", "how is", "market for"])
    
    st.session_state.debug_info.append(f"Is research request: {is_research_request}")
    
    # Process the request
    if is_research_request:
        # Initial response
        initial_response = f"I'll research '{prompt}' for {geographic_focus} over {time_period}. This will take a moment..."
        st.session_state.messages.append({"role": "assistant", "content": initial_response})
        st.session_state.debug_info.append("Added initial response message")
        st.rerun()
        
        # Conduct research and add results
        if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["content"] == initial_response:
            st.session_state.debug_info.append("Starting research after initial response")
            
            result = conduct_research(
                prompt, 
                depth=research_depth.lower(),
                region=geographic_focus,
                time_frame=time_period
            )
            
            st.session_state.debug_info.append("Research complete, processing result")
            
            if isinstance(result, str):
                # Just show error message
                st.session_state.messages[-1]["content"] = result
                st.session_state.debug_info.append("Error result, updating message")
            else:
                # Update with research results
                research_response = f"Here's what I found about {prompt} in {geographic_focus} over {time_period}:\n\n{result['content'][:500]}..."
                st.session_state.messages[-1]["content"] = research_response
                st.session_state.messages[-1]["research_results"] = result
                st.session_state.current_topic = prompt
                st.session_state.debug_info.append("Updated message with research results")
            
            st.rerun()
    else:
        # For non-research queries, just respond conversationally
        response = "I'm a market research assistant. I can help you research markets, industries, and companies. Try asking something like 'Research the electric vehicle market' or 'Tell me about AI startups'."
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.debug_info.append("Added conversational response")
        st.rerun()

# Display debug information in a footer
with st.expander("Debug Information", expanded=False):
    st.write("Recent Debug Messages:")
    for i, msg in enumerate(st.session_state.debug_info[-30:]):  # Show last 30 debug messages
        st.text(f"{i+1}. {msg}")
