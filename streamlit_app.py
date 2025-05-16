import streamlit as st
import openai
import time
import json
import logging
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

# App title and description
st.title("AI Market Research Assistant")
st.caption("Ask me about any market, industry, or company")

# Sidebar
with st.sidebar:
    st.title("Market Research AI")
    st.subheader("Settings")
    
    # API Key input
    api_key = st.text_input("OpenAI API Key", type="password")
    if api_key:
        openai.api_key = api_key
    
    # Research depth
    research_depth = st.select_slider(
        "Research Depth",
        options=["Basic", "Standard", "Detailed"],
        value="Standard",
        help="Control the depth of research (affects processing time)"
    )
    
    # Quick research topics
    st.subheader("Quick Research Topics")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("EV Market"):
            st.session_state.messages.append({"role": "user", "content": "Research electric vehicle market trends"})
            st.rerun()
        
        if st.button("AI Startups"):
            st.session_state.messages.append({"role": "user", "content": "Research AI startup landscape 2024"})
            st.rerun()
    
    with col2:
        if st.button("Health Tech"):
            st.session_state.messages.append({"role": "user", "content": "Research health technology sector"})
            st.rerun()
        
        if st.button("Renewable Energy"):
            st.session_state.messages.append({"role": "user", "content": "Research renewable energy market"})
            st.rerun()
    
    # Clear conversation
    if st.button("Clear Conversation", type="primary"):
        st.session_state.messages = []
        st.session_state.current_topic = None
        st.rerun()

# Function to conduct market research
def conduct_research(topic, depth="standard"):
    try:
        st.session_state.research_in_progress = True
        
        # Create system message for detailed research
        system_message = f"""You are an expert market research assistant. 
        Conduct detailed research on: {topic}.
        Research depth: {depth}
        
        Your response should include:
        1. Market overview
        2. Key players and companies
        3. Market size and growth trends
        4. Future outlook and predictions
        5. Challenges and opportunities
        
        Format your response using markdown with clear sections and bullet points.
        Include data and statistics where relevant.
        """
        
        # Display thinking message
        thinking_message = "I'm analyzing this topic and conducting research. This might take a minute..."
        st.chat_message("assistant").write(thinking_message)
        
        # Use OpenAI API
        if not openai.api_key:
            return "Please enter your OpenAI API key in the sidebar to continue."
        
        # Get current timestamp for research metadata
        timestamp = datetime.now().isoformat()
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Research this topic in detail: {topic}"}
            ],
            temperature=0.7,
        )
        
        # Extract research result
        research_result = response.choices[0].message.content
        
        # Extract sections for detailed view
        sections = extract_sections(research_result)
        
        # Create final result with metadata
        result = {
            "content": research_result,
            "sections": sections,
            "metadata": {
                "topic": topic,
                "depth": depth,
                "timestamp": timestamp
            }
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Error in research: {str(e)}")
        return f"I encountered an error while researching {topic}: {str(e)}"
    
    finally:
        st.session_state.research_in_progress = False

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

# User input
if prompt := st.chat_input("Ask about any market or industry..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Check if this is a research request
    is_research_request = any(keyword in prompt.lower() for keyword in 
                             ["research", "analyze", "tell me about", "what is", "how is", "market for"])
    
    # Process the request
    if is_research_request:
        # Initial response
        initial_response = f"I'll research '{prompt}' for you. This will take a moment..."
        st.session_state.messages.append({"role": "assistant", "content": initial_response})
        st.rerun()
        
        # Conduct research and add results
        if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["content"] == initial_response:
            result = conduct_research(prompt, research_depth.lower())
            
            if isinstance(result, str):
                # Just show error message
                st.session_state.messages[-1]["content"] = result
            else:
                # Update with research results
                research_response = f"Here's what I found about {prompt}:\n\n{result['content'][:500]}..."
                st.session_state.messages[-1]["content"] = research_response
                st.session_state.messages[-1]["research_results"] = result
                st.session_state.current_topic = prompt
            
            st.rerun()
    else:
        # For non-research queries, just respond conversationally
        response = "I'm a market research assistant. I can help you research markets, industries, and companies. Try asking something like 'Research the electric vehicle market' or 'Tell me about AI startups'."
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()
