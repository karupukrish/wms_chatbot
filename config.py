import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("⚠️ OPENAI_API_KEY not found! Please add it to your .env file.")

# ✅ Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ MySQL Database config
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAME", "wms_db"),
}

VECTOR_DIR = os.getenv("VECTOR_DIR", "vectorstore.index")
DATA_DIR = os.getenv("DATA_DIR", "data")
CSV_FILE = os.path.join(DATA_DIR, "All_Party_Report_csv.csv")
