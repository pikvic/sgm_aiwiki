import os
import dotenv

dotenv.load_dotenv()

TOKEN = os.getenv("TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
MONGO_DATABASE = os.getenv("MONGO_DATABASE")