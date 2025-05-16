import streamlit as st
import openai
import time
import json
import logging
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "research_in_progress" not in st.session_state:
    st.session_state.research_in_progress = False

if "current_topic" not in st.session_state:
    st.session_state.current_topic = None

if "research_queue" not in st.session_state:
    st.session_state.research_queue = None

if "debug_info" not in st.session_state:
    st.session_state.debug_info = []

# Add API Key handling
try:
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "Invalid key format"
        st.session_state.debug_info.append(f"API Key from secrets: {masked_key}")
        openai.api_key = api_key
except Exception as e:
    st.session_state.debug_info.append(f"Error with API key: {str(e)}")
    st.error(f"Error accessing API key: {str(e)}")

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
    
    # Quick research topics
    st.subheader("Quick Research Topics")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("EV Market"):
            st.session_state.messages.append({"role": "user", "content": "Research electric vehicle market trends"})
            st.session_state.research_queue = "Research electric vehicle market trends"
            st.rerun()
        
        if st.button("AI Startups"):
            st.session_state.messages.append({"role": "user", "content": "Research AI startup landscape 2024"})
            st.session_state.research_queue = "Research AI startup landscape 2024"
            st.rerun()
    
    with col2:
        if st.button("Health Tech"):
            st.session_state.messages.append({"role": "user", "content": "Research health technology sector"})
            st.session_state.research_queue = "Research health technology sector"
            st.rerun()
        
        if st.button("Renewable Energy"):
            st.session_state.messages.append({"role": "user", "content": "Research renewable energy market"})
            st.session_state.research_queue = "Research renewable energy market"
            st.rerun()
    
    # Clear conversation
    if st.button("Clear Conversation", type="primary"):
        st.session_state.messages = []
        st.session_state.current_topic = None
        st.session_state.research_queue = None
        st.rerun()
    
    # Show API status
    if openai.api_key:
        st.success("✅ OpenAI API key configured")
    else:
        st.error("❌ OpenAI API key missing")
    
    # Debug information
    with st.expander("Debug Information", expanded=False):
        st.write("Debug Messages:")
        for msg in st.session_state.debug_info[-10:]:
            st.text(msg)

# Function to conduct market research
def conduct_research(topic, depth="standard", region="Global", time_frame="Recent (Last 1-2 years)"):
    try:
        st.session_state.debug_info.append(f"Starting research on: {topic}")
        
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
        
        # Get current timestamp for research metadata
        timestamp = datetime.now().isoformat()
        st.session_state.debug_info.append(f"About to call OpenAI API at {timestamp}")
        
        # Call OpenAI API
        try:
            # Make the API call with progress spinner
            with st.spinner(f"Researching {topic} for {region} over {time_frame}... This may take up to 30 seconds"):
                st.session_state.debug_info.append("Making API call to OpenAI...")
                start_time = time.time()
                
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"Research this topic in detail: {topic} in {region} over {time_frame}"}
                    ],
                    temperature=0.7,
                )
                
                elapsed_time = time.time() - start_time
                st.session_state.debug_info.append(f"OpenAI API call completed in {elapsed_time:.2f} seconds")
                
                # Extract research result
                research_result = response.choices[0].message.content
                st.session_state.debug_info.append(f"Received response of length: {len(research_result)}")
                
                # Extract sections for detailed view
                sections = extract_sections(research_result)
                
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
                
                return result
                
        except Exception as api_error:
            st.session_state.debug_info.append(f"OpenAI API error: {str(api_error)}")
            st.session_state.debug_info.append(traceback.format_exc())
            return f"Error calling OpenAI API: {str(api_error)}"
    
    except Exception as e:
        st.session_state.debug_info.append(f"General research error: {str(e)}")
        st.session_state.debug_info.append(traceback.format_exc())
        return f"I encountered an error while researching {topic}: {str(e)}"

# Function to extract sections from research result
def extract_sections(text):
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

# Display chat messages
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

# Handle direct research execution (from queue)
if st.session_state.research_queue:
    topic = st.session_state.research_queue
    st.session_state.debug_info.append(f"Processing research queue: {topic}")
    
    # Add initial response if not already present
    if not any(msg.get("content", "").startswith(f"I'll research '{topic}'") for msg in st.session_state.messages if msg["role"] == "assistant"):
        initial_response = f"I'll research '{topic}' for {geographic_focus} over {time_period}. This will take a moment..."
        st.session_state.messages.append({"role": "assistant", "content": initial_response})
        st.session_state.debug_info.append("Added initial response")
        st.rerun()
    
    # Execute the research
    st.session_state.debug_info.append("Executing research function")
    result = conduct_research(
        topic,
        depth=research_depth.lower(),
        region=geographic_focus,
        time_frame=time_period
    )
    
    # Clear the queue to prevent re-execution
    st.session_state.research_queue = None
    
    # Update the response
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "assistant" and msg["content"].startswith(f"I'll research '{topic}'"):
            if isinstance(result, str) and result.startswith("Error"):
                st.session_state.messages[i]["content"] = result
            else:
                research_response = f"Here's what I found about {topic} in {geographic_focus} over {time_period}:\n\n{result['content'][:500]}..."
                st.session_state.messages[i]["content"] = research_response
                st.session_state.messages[i]["research_results"] = result
            break
    
    st.session_state.debug_info.append("Research completed and response updated")
    st.rerun()

# User input
if prompt := st.chat_input("Ask about any market or industry..."):
    st.session_state.debug_info.append(f"User input received: {prompt[:30]}...")
    
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Check if this is a research request
    is_research_request = any(keyword in prompt.lower() for keyword in 
                             ["research", "analyze", "tell me about", "what is", "how is", "market for"])
    
    if is_research_request:
        # Queue the research topic
        st.session_state.research_queue = prompt
    else:
        # For non-research queries, just respond conversationally
        response = "I'm a market research assistant. I can help you research markets, industries, and companies. Try asking something like 'Research the electric vehicle market' or 'Tell me about AI startups'."
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()

# Debug expander at the bottom
with st.expander("Debug Information", expanded=False):
    st.write("Recent Debug Messages:")
    for i, msg in enumerate(st.session_state.debug_info[-30:]):
        st.text(f"{i+1}. {msg}")
