from flask import Blueprint, jsonify, request

from msgraph.generated.models.o_data_errors.o_data_error import ODataError
import json
import requests
from core import graph


excel = Blueprint('excel', __name__)

base_url = 'https://graph.microsoft.com/v1.0'