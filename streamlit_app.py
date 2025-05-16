import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from the package
from market_research.app import main

# Run the main function
if __name__ == "__main__":
    main()
