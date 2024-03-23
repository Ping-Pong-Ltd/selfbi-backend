# from cryptography.fernet import Fernet
from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from core.graph import Graph
from core.common.variables import (
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_TENANT_ID,
    DB_NAME,
    DB_PWD,
    DB_SERVER,
    DB_USER,
    SQL_ACLCHEMY_KEY,
)

# fernet key for encrypting and decrypting data
# fernet = Fernet(FERNET_KEY"))

login_manager = LoginManager()
db = SQLAlchemy()
config = {
    "azure": {
        "tenantId": AZURE_TENANT_ID,
        "clientId": AZURE_CLIENT_ID,
        "clientSecret": AZURE_CLIENT_SECRET,
    }
}
azure_settings = config["azure"]
graph: Graph = Graph(azure_settings)


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config["SECRET_KEY"] = SQL_ACLCHEMY_KEY
    
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql://{DB_USER}:{DB_PWD}@{DB_SERVER}/{DB_NAME}"
    )
    db.init_app(app)
    login_manager.init_app(app)
    from core.apis import dashboard, excel, home, services, users

    app.register_blueprint(home.home)
    app.register_blueprint(dashboard.dashboard)
    app.register_blueprint(excel.excel)
    app.register_blueprint(users.users)
    app.register_blueprint(services.services)

    return app
