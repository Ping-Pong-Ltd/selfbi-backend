import os
from dotenv import load_dotenv

load_dotenv(".env")

RUN_MODE = os.getenv("RUN_MODE")
FERNET_KEY = os.getenv("FERNET_KEY")

# MICROSOFT GRAPH
DRIVE_ID = os.getenv("DRIVE_ID")
USER_ID = os.getenv("USER_ID")
SITE_ID = os.getenv("SITE_ID")
MG_BASE_URL = "https://graph.microsoft.com/v1.0"

# AZURE
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# DATABASE
DB_SERVER = os.getenv("DB_SERVER")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PWD = os.getenv("DB_PWD")
SQL_ACLCHEMY_KEY = os.getenv("SQL_ACLCHEMY_KEY")
