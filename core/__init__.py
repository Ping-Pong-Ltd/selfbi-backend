from flask import Flask
from flask_cors import CORS
from cryptography.fernet import Fernet
import os
import configparser
from core.graph import Graph

# fernet key for encrypting and decrypting data
# fernet = Fernet(os.getenv("FERNET_KEY"))

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.getenv("SQL_ACLCHEMY_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

config = configparser.ConfigParser()
config.read(['config.cfg'])
azure_settings = config['azure']
graph: Graph = Graph(azure_settings)

from core.views import home
from core.views import dashboard

app.register_blueprint(home.home)
app.register_blueprint(dashboard.dashboard)

