import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.requirement_checker import recheck_all_articles

if __name__ == "__main__":
    recheck_all_articles()
