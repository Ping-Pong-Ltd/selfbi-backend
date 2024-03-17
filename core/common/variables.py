import os
from dotenv import load_dotenv

load_dotenv(".env")

DRIVE_ID = os.getenv("DRIVE_ID")
USER_ID = os.getenv("USER_ID")
SITE_ID = os.getenv("SITE_ID")
MG_BASE_URL = "https://graph.microsoft.com/v1.0"
