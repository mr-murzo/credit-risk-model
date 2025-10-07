from dotenv import load_dotenv
import os

load_dotenv()
UPLOAD_PASSWORD=os.getenv("UPLOAD_PASSWORD")
POSTGRES_USER=os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB=os.getenv("POSTGRES_DB")

