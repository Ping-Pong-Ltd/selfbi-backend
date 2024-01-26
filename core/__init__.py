from flask import Flask
from cryptography.fernet import Fernet
import os

# fernet key for encrypting and decrypting data
# fernet = Fernet(os.getenv("FERNET_KEY"))

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv("SQL_ACLCHEMY_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

from core.views import home

app.register_blueprint(home.home)
