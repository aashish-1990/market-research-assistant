import streamlit as st
import openai
import time
import json
import logging
import traceback
import re
import random
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation enhancement functions
def get_greeting_response():
    greetings = [
        "Hello! How can I help with your market research today?",
        "Hi there! I'm ready to assist with any market research questions you have.",
        "Welcome! I'd be happy to research any industry or market for you.",
        "Hey! What market or industry would you like to explore today?",
        "Greetings! I'm your market research assistant. What would you like to know about?"
    ]
    return random.choice(greetings)

def get_acknowledgment():
    acknowledgments = [
        "I understand you'd like to know about",
        "I'll research",
        "I'd be happy to look into",
        "Let me gather information about",
        "I'll find the latest insights on"
    ]
    return random.choice(acknowledgments)

def get_follow_up_question(topic):
    questions = [
        f"Is there any specific aspect of {topic} you're most interested in?",
        f"Would you like me to focus on any particular trends in {topic}?",
        f"Are you looking for information about any specific companies in the {topic} space?",
        f"Is there a particular region you're most interested in for {topic}?",
        f"Are you interested in recent developments or longer-term trends in {topic}?"
    ]
    return random.choice(questions)

def get_transition_phrase():
    phrases = [
        "Based on my research,",
        "Here's what I found:",
        "According to the latest information,",
        "After analyzing the market,",
        "My research indicates that"
    ]
    return random.choice(phrases)

# Content filtering function
def filter_inappropriate_content(text):
    # List of inappropriate terms (simplified - expand as needed)
    inappropriate_terms = [
        "profanity", "offensive", "vulgar", "inappropriate"
        # Add actual terms here
    ]
    
    # Check if any inappropriate terms are in the text
    has_inappropriate = any(term in text.lower() for term in inappropriate_terms)
    
    if has_inappropriate:
        return True, "I'm here to help with market research queries. Could you please rephrase your question in professional terms?"
    
    return False, text

# Enhanced intent classification
def classify_intent(text):
    # Normalize text for better matching
    text_lower = text.lower().strip()
    
    # Check for greetings
    greeting_patterns = [
        r'^hi\b', r'^hello\b', r'^hey\b', r'^greetings\b', 
        r'^good morning\b', r'^good afternoon\b', r'^good evening\b'
    ]
    if any(re.match(pattern, text_lower) for pattern in greeting_patterns):
        return "greeting", {}
    
    # Check for thanks
    thanks_patterns = [
        r'thank you', r'thanks', r'appreciate', r'grateful'
    ]
    if any(pattern in text_lower for pattern in thanks_patterns):
        return "thanks", {}
    
    # Check for research requests - more comprehensive patterns
    research_patterns = [
        r'research', r'analyze', r'study', r'investigate', r'look into',
        r'tell me about', r'what is', r'how is', r'market for', r'industry',
        r'information on', r'data about', r'statistics', r'trends', r'growth'
    ]
    
    if any(pattern in text_lower for pattern in research_patterns):
        # Extract topic
        topic = text
        for pattern in ['research', 'tell me about', 'information on', 'data about', 
                        'what is', 'how is', 'analyze', 'study', 'investigate']:
            if pattern in text_lower:
                topic = re.sub(f'{pattern}\\s+', '', topic, flags=re.IGNORECASE)
                
        return "research_request", {"topic": topic.strip()}
    
    # Check for parameter change requests
    parameter_patterns = [
        r'change (region|location|area|geography|country|focus)',
        r'update (region|location|area|geography|country|focus)',
        r'different (region|location|area|geography|country|focus)',
        r'change (time|period|timeframe|years)',
        r'update (time|period|timeframe|years)',
        r'different (time|period|timeframe|years)',
        r'change (depth|detail|level)',
        r'update (depth|detail|level)',
        r'different (depth|detail|level)'
    ]
    
    if any(re.search(pattern, text_lower) for pattern in parameter_patterns):
        return "parameter_change", {"original_text": text}
    
    # Check for follow-up questions about previous research
    followup_patterns = [
        r'tell me more', r'more details', r'elaborate', r'expand on',
        r'what about', r'how about', r'can you explain', r'additional info'
    ]
    
    if any(pattern in text_lower for pattern in followup_patterns):
        # Try to identify the aspect they want to know more about
        aspect = None
        aspects = ['trends', 'players', 'companies', 'growth', 'challenges', 
                   'opportunities', 'regulations', 'future', 'forecast', 'competitors']
        
        for a in aspects:
            if a in text_lower:
                aspect = a
                break
                
        return "followup_question", {"aspect": aspect}
    
    # Default to general query
    return "general_query", {"text": text}

# Extract research topic from previous messages
def extract_research_topic():
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant" and "research_results" in msg:
            topic = msg.get("research_results", {}).get("metadata", {}).get("topic", "")
            if topic:
                return topic
    return None

# Access API key from Streamlit secrets
try:
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "Invalid key format"
        openai.api_key = api_key
except Exception as e:
    st.error(f"Error accessing API key: {str(e)}")

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

if "last_parameters" not in st.session_state:
    st.session_state.last_parameters = {
        "depth": "Standard",
        "region": "Global",
        "time_period": "Recent (Last 1-2 years)"
    }

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
        value=st.session_state.last_parameters.get("depth", "Standard"),
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
        index=geographic_options.index(st.session_state.last_parameters.get("region", "Global")),
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
        index=time_period_options.index(st.session_state.last_parameters.get("time_period", "Recent (Last 1-2 years)")),
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
    
    # Debug information (hidden in production)
    with st.expander("Debug Information", expanded=False):
        st.write("Debug Messages:")
        for msg in st.session_state.debug_info[-10:]:
            st.text(msg)

# Check if parameters changed
if (research_depth != st.session_state.last_parameters["depth"] or
    geographic_focus != st.session_state.last_parameters["region"] or
    time_period != st.session_state.last_parameters["time_period"]):
    
    # Get current research topic
    current_topic = extract_research_topic()
    
    if current_topic:
        # Update the parameters
        st.session_state.last_parameters = {
            "depth": research_depth,
            "region": geographic_focus,
            "time_period": time_period
        }
        
        # Queue a new research with updated parameters
        st.session_state.research_queue = current_topic
        
        # Add a message about parameter change
        parameter_message = f"I notice you've changed the research parameters. Let me update my research on '{current_topic}' for {geographic_focus} over {time_period}."
        st.session_state.messages.append({"role": "assistant", "content": parameter_message})
        
        st.rerun()

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
        Make your response conversational and human-like, not too formal.
        """
        
        # Get current timestamp for research metadata
        timestamp = datetime.now().isoformat()
        
        # Call OpenAI API
        try:
            # Make the API call with progress spinner
            with st.spinner(f"Researching {topic} for {region} over {time_frame}... This may take up to 30 seconds"):
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
                        "region": region,
                        "time_frame": time_frame,
                        "timestamp": timestamp,
                        "processing_time": f"{elapsed_time:.2f} seconds"
                    }
                }
                
                return result
                
        except Exception as api_error:
            st.session_state.debug_info.append(f"OpenAI API error: {str(api_error)}")
            return f"Error calling OpenAI API: {str(api_error)}"
    
    except Exception as e:
        st.session_state.debug_info.append(f"General research error: {str(e)}")
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
    
    # Add initial response if not already present
    exists = False
    for msg in st.session_state.messages:
        if msg["role"] == "assistant" and msg["content"].startswith(f"I'll research '{topic}'"):
            exists = True
            break
            
    if not exists:
        initial_response = f"{get_acknowledgment()} '{topic}' for {geographic_focus} over {time_period}. This will take a moment..."
        st.session_state.messages.append({"role": "assistant", "content": initial_response})
        st.rerun()
    
    # Execute the research
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
        if msg["role"] == "assistant" and msg["content"].startswith(f"{get_acknowledgment()[:15]}") and "'{topic}'" in msg["content"]:
            if isinstance(result, str) and result.startswith("Error"):
                st.session_state.messages[i]["content"] = result
            else:
                research_response = f"{get_transition_phrase()} {result['content'][:500]}..."
                st.session_state.messages[i]["content"] = research_response
                st.session_state.messages[i]["research_results"] = result
                
                # Add a follow-up question
                follow_up = get_follow_up_question(topic)
                if not follow_up in st.session_state.messages[i]["content"]:
                    st.session_state.messages[i]["content"] += f"\n\n{follow_up}"
            break
    
    st.rerun()

# User input
if prompt := st.chat_input("Ask about any market or industry..."):
    # Filter inappropriate content
    is_inappropriate, filtered_prompt = filter_inappropriate_content(prompt)
    
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    if is_inappropriate:
        # Respond to inappropriate content
        st.session_state.messages.append({"role": "assistant", "content": filtered_prompt})
        st.rerun()
    
    # Classify intent
    intent_type, intent_params = classify_intent(prompt)
    
    if intent_type == "greeting":
        response = get_greeting_response()
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    elif intent_type == "thanks":
        response = "You're welcome! I'm happy to help with your market research needs. Is there anything else you'd like to know?"
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    elif intent_type == "research_request":
        # Queue the research topic
        topic = intent_params.get("topic", prompt)
        st.session_state.research_queue = topic
    
    elif intent_type == "parameter_change":
        current_topic = extract_research_topic()
        if current_topic:
            # Update the parameters and queue a new research
            st.session_state.last_parameters = {
                "depth": research_depth,
                "region": geographic_focus,
                "time_period": time_period
            }
            st.session_state.research_queue = current_topic
            
            response = f"I'll update my research on '{current_topic}' with your new parameters: {geographic_focus} region over {time_period} timeframe."
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            response = "I don't have any previous research to update. Would you like me to research a specific topic for you?"
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    elif intent_type == "followup_question":
        current_topic = extract_research_topic()
        aspect = intent_params.get("aspect")
        
        if current_topic:
            if aspect:
                response = f"Let me provide more information about {aspect} related to {current_topic}."
                # Here you could make a more targeted research call specifically about this aspect
                # For now, we'll just queue a new general research
                st.session_state.research_queue = f"{current_topic} {aspect}"
            else:
                response = f"I'd be happy to provide more details about {current_topic}. Is there a specific aspect you're interested in?"
                st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            response = "I don't have previous research to elaborate on. Could you specify what topic you'd like me to research?"
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    else:  # general_query or unknown
        # For general queries, respond conversationally
        response = "I'm your market research assistant. I can help you research markets, industries, and companies. Try asking something like 'Research the electric vehicle market' or 'Tell me about AI startups'."
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()

# Initialize with a greeting if there are no messages
if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": get_greeting_response()})
    st.rerun()

# Debug expander at the bottom (hidden in production)
with st.expander("Debug Information", expanded=False):
    st.write("Recent Debug Messages:")
    for i, msg in enumerate(st.session_state.debug_info[-30:]):
        st.text(f"{i+1}. {msg}")
