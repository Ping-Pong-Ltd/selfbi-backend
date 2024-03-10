import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from core.graph import Graph

# fernet key for encrypting and decrypting data
# fernet = Fernet(os.getenv("FERNET_KEY"))
load_dotenv(".env")

app = Flask(__name__)
CORS(app)

app.config["SECRET_KEY"] = os.getenv("SQL_ACLCHEMY_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

config = {
    "azure": {
        "tenantId": os.getenv("AZURE_TENANT_ID"),
        "clientId": os.getenv("AZURE_CLIENT_ID"),
        "clientSecret": os.getenv("AZURE_CLIENT_SECRET"),
    }
}

azure_settings = config["azure"]
graph: Graph = Graph(azure_settings)


from core.views import dashboard, excel, home

app.register_blueprint(home.home)
app.register_blueprint(dashboard.dashboard)
app.register_blueprint(excel.excel)
