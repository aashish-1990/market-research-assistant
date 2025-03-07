 Market Research Tool (Using GPT-4o-mini with Memory)
=============================================================

This tool performs market research on a user-provided topic (e.g., "fintech") or company, leveraging CrewAI, GPT-4o-mini, and web scraping/search tools. It generates a detailed summary with trends, leaders, financial insights, and more. This README guides you—whether beginner or advanced—through setting up and running the tool on macOS, Windows, Linux, or online terminals.

Overview
--------
- Purpose: Research topics or companies with structured outputs (8 sections).
- Features: Memory-enabled agents, human feedback verification, web search/scraping.
- Requirements: Python 3.10+, API keys (OpenAI, Serper), dependencies.

Prerequisites
-------------
Before running, ensure you have:
1. Python 3.10 or higher installed (3.11/3.12 also work).
2. Git installed (optional, for cloning).
3. An internet connection.
4. API keys for OpenAI and Serper (steps below).

Step 1: Get API Keys
--------------------
You need two API keys to run this tool. Follow these steps to obtain them:

### OpenAI API Key
1. Go to: https://platform.openai.com
2. Sign up or log in with your OpenAI account.
3. Navigate to: Dashboard > API Keys (left sidebar).
4. Click "Create new secret key":
   - Name it (e.g., "market-research-tool").
   - Copy the key (e.g., "sk-...") immediately—it won’t show again.
5. Store it securely (you’ll add it to `.env` later).

### Serper API Key
1. Go to: https://serper.dev
2. Sign up or log in (Google login supported).
3. Navigate to: Dashboard.
4. Find your API key (e.g., "5906fc48...") under "Your API Key".
5. Copy it and store it securely.

Step 2: Set Up Your Environment
-------------------------------
Clone the repo and configure your system.

### Option 1: Local Machine (macOS, Windows, Linux)
#### Clone the Repository
1. Open a terminal (macOS/Linux: Terminal, Windows: Command Prompt/PowerShell):
   - macOS/Linux: Use built-in Terminal.
   - Windows: Use Command Prompt (`cmd`), PowerShell, or Git Bash (install Git from https://git-scm.com if needed).
2. Run:
git clone https://github.com/yourusername/market-research-tool.git
cd market-research-tool

- Replace "yourusername" with your GitHub username.
- If Git isn’t installed, download the ZIP from GitHub and extract it manually.

#### Install Python (If Not Installed)
- **macOS**:
- Check: `python3 --version`
- Install (if missing): `brew install python` (install Homebrew first: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`).
- **Windows**:
- Download: https://www.python.org/downloads (e.g., Python 3.11).
- Install: Run the installer, check "Add Python to PATH", then finish.
- Verify: `python --version` (or `python3 --version` in some cases).
- **Linux**:
- Check: `python3 --version`
- Install (Ubuntu/Debian): `sudo apt update && sudo apt install python3 python3-pip`
- Install (Fedora): `sudo dnf install python3 python3-pip`

#### Create a Virtual Environment
1. Create:
- macOS/Linux: `python3 -m venv venv`
- Windows: `python -m venv venv`
2. Activate:
- macOS/Linux: `source venv/bin/activate`
- Windows (Command Prompt): `venv\Scripts\activate`
- Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
3. Verify: Your terminal prompt should show `(venv)`.

#### Install Dependencies
1. Ensure `requirements.txt` is in the directory.
2. Run:
pip install -r requirements.txt

- This installs `crewai`, `langchain-openai`, `crewai_tools`, `python-dotenv`, etc.
- If errors occur, update pip: `pip install --upgrade pip`.

### Option 2: Online Terminal (e.g., Replit, Google Colab)
#### Replit
1. Go to: https://replit.com
2. Sign up or log in.
3. Create a new Repl:
- Language: Python.
- Import from GitHub: Paste `https://github.com/yourusername/market-research-tool`.
4. Install dependencies:
- In the shell: `pip install -r requirements.txt`.

#### Google Colab
1. Go to: https://colab.research.google.com
2. File > Upload Notebook > Upload `simple_research.py` (or fetch from GitHub).
3. Add a cell at the top:
!pip install -r requirements.txt
!git clone https://github.com/yourusername/market-research-tool.git
%cd market-research-tool

4. Run the cell before executing the script.

Step 3: Configure API Keys in `.env`
-----------------------------------
1. Create a `.env` file in the `market-research-tool` directory:
- **macOS/Linux**:
touch .env
nano .env

- **Windows (Command Prompt)**:
echo. > .env
notepad .env

- **Windows (PowerShell)**:
New-Item .env
notepad .env

- **Replit**: Use the "Files" pane, click "New File", name it `.env`.
- **Colab**: Add a cell:

%%writefile .env
OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=your_serper_key_here


2. Add your keys:
OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=your_serper_key_here

- Replace placeholders with the keys you got in Step 1.
- Save:
  - Nano: `Ctrl + X`, `Y`, `Enter`.
  - Notepad: File > Save, close.
  - Replit/Colab: Save/close the editor.

3. Verify (optional):
- macOS/Linux: `cat .env`
- Windows: `type .env`
- Ensure keys are correct without extra spaces.

Step 4: Run the Code
--------------------
1. **Local Machine**:
- Ensure virtual environment is active:
  - macOS/Linux: `(venv) $`
  - Windows: `(venv) C:\...>`
- Run:
python3 simple_research.py  # macOS/Linux
python simple_research.py   # Windows


2. **Replit**:
- Click "Run" button or type in shell:

python3 simple_research.py


3. **Google Colab**:
- Add a cell:

%run simple_research.py

- Execute the cell.

4. **Interaction**:
- Enter a query (e.g., "fintech").
- Provide depth (e.g., "detailed"), location (e.g., "global"), timeframe (e.g., "5 years"), type (1=company, 2=keyword).
- Review the summary, respond (e.g., "looks good") when prompted.

Troubleshooting
---------------
- **Error: "Missing API keys!"**:
- Check `.env` exists and has both keys.
- Ensure no typos or extra spaces (e.g., `OPENAI_API_KEY=sk-...`, not `OPENAI_API_KEY = sk-...`).
- **ModuleNotFoundError**:
- Run `pip install -r requirements.txt` again.
- **Permission Denied**:
- macOS/Linux: `chmod +x simple_research.py`
- Windows: Run terminal as administrator.
- **Online Terminal Issues**:
- Replit: Ensure `.env` is in the file list (hidden by default—click "Show hidden files").
- Colab: Verify `.env` cell ran successfully.

Additional Notes
----------------
- **OS Compatibility**: Works on macOS, Windows, Linux, and online platforms with Python 3.10+.
- **Dependencies**: Listed in `requirements.txt`—install with `pip`.
- **Memory**: Agents retain context within a run; no long-term storage across sessions yet.
- **Feedback**: After verification, any input (e.g., "looks good") accepts the summary—future updates could add sentiment analysis.

For Help
--------
- Contact: [Your GitHub username or email if you choose to share]
- Issues: File a GitHub issue at https://github.com/yourusername/market-research-tool/issues

Enjoy researching with this tool!
