import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

from core.graph import Graph

# fernet key for encrypting and decrypting data
# fernet = Fernet(os.getenv("FERNET_KEY"))
load_dotenv(".env")
login_manager = LoginManager()
db = SQLAlchemy()
config = {
    "azure": {
        "tenantId": os.getenv("AZURE_TENANT_ID"),
        "clientId": os.getenv("AZURE_CLIENT_ID"),
        "clientSecret": os.getenv("AZURE_CLIENT_SECRET"),
    }
}
azure_settings = config["azure"]
graph: Graph = Graph(azure_settings)


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config["SECRET_KEY"] = os.getenv("SQL_ACLCHEMY_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
    db.init_app(app)
    login_manager.init_app(app)
    
    
    
    from core.views import dashboard, excel, home, users
    
    
    app.register_blueprint(home.home)
    app.register_blueprint(dashboard.dashboard)
    app.register_blueprint(excel.excel)
    app.register_blueprint(users.users)
    
    
    return app
