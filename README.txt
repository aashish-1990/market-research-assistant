Conversational Market Research Assistant
A powerful, conversational AI assistant for conducting comprehensive market research, built withCrewAI, LangChain, and Streamlit.
Features
Natural Conversation
: Chat naturally with the AI to request market research on any topic,company, or industry
Voice Interaction
: Enable voice mode to speak with the assistant and hear research results
Comprehensive Research
: Leverages multiple specialized AI agents to deliver thorough researchresults
Structured Output
: Research is organized into clear sections with bulleted insights
Research Caching
: Cache research results to avoid redundant queries and speed up responses
Quick Topics
: Pre-defined research topics for one-click research
Architecture
The application uses a modular architecture with several key components:
Research Engine
: Specialized CrewAI agents for research, analysis, verification, and contentcreation
Dialog Management
: Intent recognition and natural conversation handling
Voice Processing
: Optional speech-to-text and text-to-speech capabilities
Web Interface
: Streamlit-based UI for easy interaction
Installation
Prerequisites
Python 3.9 or higher
API keys for:
OpenAI (for the language model)
Serper (for web search capabilities)
ElevenLabs (optional, for high-quality voice synthesis)
Step 1: Clone the repository
Step 2: Set up a virtual environment (optional but recommended)
Step 3: Install dependencies
Step 4: Configure environment variables
Create a
.env
file in the root directory using the provided
.env.example
as a template:
Edit the
.env
file to add your API keys:
Usage
Starting the application
This will launch the Streamlit application in your default web browser.
bash
git
clone https://github.com/yourusername/market-research-assistant.git
cd
market-research-assistant
bash
python -m venv venv
source
venv/bin/activate
# On Windows: venv\Scripts\activate
bash
pip
install
-r requirements.txt
bash
cp
.env.example .env
OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=your_serper_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
bash
streamlit run market_research/app.py
Basic interaction
1.
Type your research query in the input box, e.g., "Research the electric vehicle market in Europe"
2.
The assistant will acknowledge your request and begin the research process
3.
Once complete, you'll see a detailed report with organized sections and insights
4.
Ask follow-up questions to explore specific aspects of the research
Voice interaction
If voice mode is enabled:
1.
Click the microphone button to speak your query
2.
The assistant will respond verbally with a summary of findings
3.
The full written report will still be available in the chat interface
Adjusting research depth
Use the sidebar to adjust research depth:
Basic
: Faster but less detailed research
Standard
: Balanced depth and speed
Detailed
: Most comprehensive research, but takes longer to complete
Customization
Changing the AI model
You can change the AI model in the sidebar or by modifying the
.env
file:
Available models depend on your OpenAI subscription.
Adding custom research templates
You can create custom quick research buttons by modifying the
_setup_sidebar
method in
app.py
.
Project Structure
LLM_MODEL=gpt-4o
Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
License
This project is licensed under the MIT License - see the LICENSE file for details.
Acknowledgments
CrewAI
- For the agent framework
LangChain
- For the language model tools
Streamlit
- For the web interface
OpenAI
- For the language models
market_research_assistant/
├── market_research/
│ ├── config.py # Configuration management
│ ├── agents.py # Enhanced agent definitions
│ ├── research.py # Research engine
│ ├── dialog.py # Dialog management
│ ├── voice.py # Voice processing
│ ├── app.py # Streamlit application
│ └── utils/ # Utility functions
└── data/ # Directory for cached research
