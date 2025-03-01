import os
import warnings
from dotenv import load_dotenv
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
from datetime import datetime, timedelta

# Suppress warnings
warnings.filterwarnings('ignore')

# Load environment variables from .env
load_dotenv()

# Check for required API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

if not OPENAI_API_KEY or not SERPER_API_KEY:
    raise ValueError(
        "Missing API keys! Please create a '.env' file in the same directory with:\n"
        "OPENAI_API_KEY=your_openai_key_here\n"
        "SERPER_API_KEY=your_serper_key_here\n"
        "Get your OpenAI key from platform.openai.com and Serper key from serper.dev."
    )

llm = ChatOpenAI(model="gpt-4o-mini")

# Tools
search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()

# Agents with memory enabled
researcher = Agent(
    role="General Researcher",
    goal="Collect detailed raw data on any topic or company from web sources using search and scraping.",
    backstory="A thorough investigator adept at finding deep insights on any subject.",
    tools=[search_tool, scrape_tool],
    llm=llm,
    verbose=True,
    memory=True
)

summarizer = Agent(
    role="Summary Organizer",
    goal="Structure research data into clear, detailed sections with bullet points.",
    backstory="A communicator who turns complex data into organized, actionable summaries.",
    llm=llm,
    verbose=True,
    memory=True
)

verifier = Agent(
    role="Output Verifier",
    goal="Verify the summary for structure and accuracy against raw data, refining with additional checks.",
    backstory="A meticulous checker ensuring reliable and complete outputs.",
    tools=[search_tool, scrape_tool],
    llm=llm,
    verbose=True,
    memory=True
)

# Helper Functions
def get_current_date():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Using date: {today} (validated as current)")
    return today

def get_research_params():
    query = input("Enter a keyword or company name: ").strip()
    depth = input("Depth (basic/detailed, default: detailed): ").strip() or "detailed"
    location = input("Location (e.g., global, India, default: global): ").strip() or "global"
    time_frame = input("Time frame (e.g., 2 years, default: 2 years): ").strip() or "2 years"
    input_type = "company" if input("Is this a company? (1=yes, 2=no, default: 2): ").strip() in ["1", ""] else "keyword"
    return {"query": query, "depth": depth, "location": location, "time_frame": time_frame}, input_type

# Tasks
def create_research_task(params, input_type, current_date):
    time_frame_years = int(params["time_frame"].split()[0])
    start_date = (datetime.strptime(current_date, "%Y-%m-%d") - timedelta(days=365 * time_frame_years)).strftime("%Y-%m-%d")
    if input_type == "keyword":
        description = (
            f"Research the topic '{params['query']}' in {params['location']} from {start_date} to {current_date}. Find:\n"
            "- At least 5 current trends (e.g., technologies, behaviors) from news and industry reports.\n"
            "- 3+ market leaders (e.g., established companies) with their roles.\n"
            "- 3+ new comers (e.g., emerging players) from startup databases or news.\n"
            "- Financial insights (e.g., market size, ROI) from reputable sources.\n"
            "- Funding information (e.g., 3+ recent investments) from financial news or platforms like Crunchbase.\n"
            "- Future landscape (e.g., 3+ predictions) from analyst reports.\n"
            "- Growth potential (e.g., 3+ opportunities) from market studies.\n"
            "- Potential clients (e.g., 3+ target industries) using search and scraping."
        )
    else:
        description = (
            f"Research the company '{params['query']}' in {params['location']} from {start_date} to {current_date}. Find:\n"
            "- Domain (e.g., industry sector) from company site or industry reports.\n"
            "- 3+ competitors (e.g., key rivals) from market analyses.\n"
            "- Funding information (e.g., last 5 years’ investments) from company site or Crunchbase.\n"
            "- Competitive details: SWOT (collective), pricing (scrape competitor sites), market share (estimates), innovation (tech/strategies).\n"
            "- Funding of competitors (e.g., 3+ rival investments) from financial sources.\n"
            "- Target customers (e.g., current clients) from company data.\n"
            "- Grants/funds for target customers (e.g., in the domain) from government or industry reports.\n"
            "- Potential future clients (e.g., new markets) from market trends."
        )
    return Task(
        description=description,
        expected_output=f"Detailed raw findings about '{params['query']}'.",
        agent=researcher
    )

def create_summary_task(raw_data, params, input_type):
    if input_type == "keyword":
        description = (
            f"Summarize this raw data: {raw_data[:2000]}... for the topic '{params['query']}' in this structure:\n"
            "Current Trends:\n- [5+ trends with explanations]\n"
            "Market Leaders:\n- [3+ leaders with roles]\n"
            "New Comers:\n- [3+ emerging players]\n"
            "Financial Insights:\n- [3+ insights]\n"
            "Funding Information:\n- [3+ events]\n"
            "Future Landscape:\n- [3+ predictions]\n"
            "Growth Potential:\n- [3+ opportunities]\n"
            "Potential Clients:\n- [3+ industries]"
        )
    else:
        description = (
            f"Summarize this raw data: {raw_data[:2000]}... for the company '{params['query']}' in this structure:\n"
            "Domain:\n- [Sector]\n"
            "Competitors:\n- [3+ rivals]\n"
            "Funding Information:\n- [Company funding]\n"
            "Competitive Analysis:\n- Strengths: [Strengths]\n- Weaknesses: [Weaknesses]\n- Opportunities: [Opportunities]\n"
            "- Threats: [Threats]\n- Pricing: [Pricing]\n- Market Share: [Dominance]\n- Innovation: [Tech/strategies]\n"
            "Funding Information about Competitors:\n- [3+ rival funding]\n"
            "Target Customers:\n- [Current clients]\n"
            "Grants or Funds Received by Target Customers:\n- [Funds]\n"
            "Potential Future Clients:\n- [Future industries]"
        )
    return Task(
        description=description,
        expected_output="A structured summary with bullet points.",
        agent=summarizer
    )

def create_verify_task(summary, raw_data, params, input_type):
    sections = (
        ["Current Trends", "Market Leaders", "New Comers", "Financial Insights", "Funding Information", 
         "Future Landscape", "Growth Potential", "Potential Clients"] if input_type == "keyword" else
        ["Domain", "Competitors", "Funding Information", "Competitive Analysis", "Funding Information about Competitors", 
         "Target Customers", "Grants or Funds Received by Target Customers", "Potential Future Clients"]
    )
    description = (
        f"Verify this summary: {summary} against raw data: {raw_data[:2000]}... for '{params['query']}'.\n"
        f"Ensure all sections ({', '.join(sections)}) are present with at least 3 items each (where applicable).\n"
        "Validate accuracy (e.g., funding matches; scrape if unclear).\n"
        "Return the verified summary in the same structure."
    )
    return Task(
        description=description,
        expected_output="A verified, structured summary with bullet points.",
        agent=verifier,
        human_input=True
    )

# Main Function
def simple_market_research():
    params, input_type = get_research_params()
    current_date = get_current_date()
    
    research_task = create_research_task(params, input_type, current_date)
    research_crew = Crew(agents=[researcher], tasks=[research_task], memory=True)
    raw_data = research_crew.kickoff().raw
    
    summary_task = create_summary_task(raw_data, params, input_type)
    summary_crew = Crew(agents=[summarizer], tasks=[summary_task], memory=True)
    summary = summary_crew.kickoff().raw
    
    verify_task = create_verify_task(summary, raw_data, params, input_type)
    verify_crew = Crew(agents=[verifier], tasks=[verify_task], memory=True)
    verified_summary = verify_crew.kickoff().raw
    
    # Debug: Print raw verified summary
    print("\nRaw Verified Summary:")
    print(verified_summary)
    
    # Mapping for header variations
    header_mapping = {
        "Current Trends (2024-2025)": "Current Trends",
        "Current Trends": "Current Trends",
        "Market Leaders": "Market Leaders",
        "Newcomers": "New Comers",
        "New Comers": "New Comers",
        "Financial Insights": "Financial Insights",
        "Funding Information": "Funding Information",
        "Future Landscape Predictions": "Future Landscape",
        "Future Landscape": "Future Landscape",
        "Growth Potential Opportunities": "Growth Potential",
        "Growth Potential": "Growth Potential",
        "Potential Client Industries": "Potential Clients",
        "Potential Clients": "Potential Clients",
        "Domain": "Domain",
        "Competitors": "Competitors",
        "Competitive Analysis": "Competitive Analysis",
        "Funding Information about Competitors": "Funding Information about Competitors",
        "Target Customers": "Target Customers",
        "Grants or Funds Received by Target Customers": "Grants or Funds Received by Target Customers",
        "Potential Future Clients": "Potential Future Clients"
    }
    
    # Initialize result dictionary
    result = {
        "Current Trends" if input_type == "keyword" else "Domain": "",
        "Market Leaders" if input_type == "keyword" else "Competitors": "",
        "New Comers" if input_type == "keyword" else "Funding Information": "",
        "Financial Insights" if input_type == "keyword" else "Competitive Analysis": "",
        "Funding Information" if input_type == "keyword" else "Funding Information about Competitors": "",
        "Future Landscape" if input_type == "keyword" else "Target Customers": "",
        "Growth Potential" if input_type == "keyword" else "Grants or Funds Received by Target Customers": "",
        "Potential Clients" if input_type == "keyword" else "Potential Future Clients": ""
    }
    
    # Parse verified summary with mapped headers
    current_section = None
    for line in verified_summary.split("\n"):
        line = line.strip()
        if not line:
            continue
        for raw_header, mapped_key in header_mapping.items():
            if line.startswith(f"**{raw_header}**:"):
                current_section = mapped_key
                break
        if current_section and line.startswith("-"):
            result[current_section] += line + "\n"
    
    return result

# Run the Program
if __name__ == "__main__":
    print("Advanced Market Research Tool (Using GPT-4o-mini with Memory)")
    result = simple_market_research()
    print(f"\nResearch Results:")
    for section, content in result.items():
        print(f"{section}:\n{content.strip() if content.strip() else 'No data available'}\n")