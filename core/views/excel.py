import os 
from dotenv import load_dotenv

from flask import Blueprint, jsonify, request

from msgraph.generated.models.o_data_errors.o_data_error import ODataError
import requests
from core import graph

load_dotenv(".env")

excel = Blueprint('excel', __name__)

base_url = 'https://graph.microsoft.com/v1.0'
site_id = os.getenv("SITE_ID")
drive_id = os.getenv("DRIVE_ID")

@excel.route('/upload_excel', methods=['POST'])
async def upload_excel():

    relative_path = "SelfBI/ExcelDashboard/Credits/Sandbox"
    file_name = request.args.get('file_name', default=None, type=str)
    url = f"{base_url}/sites/{site_id}/drives/{drive_id}/root:/{relative_path}/{file_name}:/content"

    access_token = await graph.get_app_only_token()

    file = request.files['binary_file']
    if not file:
        return jsonify("No file found")
    
    payload = file.read()
    headers = {
    'Content-Type': 'text/plain',
    'Authorization': 'Bearer ' + access_token
    }

    response = requests.request("PUT", url, headers=headers, data=payload)

    return response.json()



@excel.route('/copy_excel', methods=['POST'])
async def copy_excel():
    item_id = request.files['item_id']
    file_name = request.files['file_name']
    url = f"{base_url}/sites/{site_id}/drives/{drive_id}/items/{item_id}/copy"

    payload = {
        "parentReference": {
            "driveId": drive_id,
            "id": item_id
        },
        "name": file_name
    }
    access_token = await graph.get_app_only_token()

    headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + access_token
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return jsonify(response.text)
