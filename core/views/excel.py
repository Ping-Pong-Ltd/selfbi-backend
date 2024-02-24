import json
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



@excel.route('/copy_excel', methods=['GET','POST'])
async def copy_excel():
    item_id = request.files['item_id']
    file_name = request.files['file_name']
    url = f"{base_url}/sites/{site_id}/drives/{drive_id}/items/{item_id}/copy"

    
    access_token = await graph.get_app_only_token()

    headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + access_token
    }
    
    # Get the item details
    item_endpoint = '/drive/items/' + item_id
    item_url = base_url + item_endpoint
    item_response = requests.request("GET", item_url, headers=headers)
    item_data = json.loads(item_response.text)
    
    # Get the parentReference
    parent_id = item_data['parentReference']['id']

    # List all items in the parent folder
    list_endpoint = '/drive/items/' + parent_id + '/children'
    list_url = base_url + list_endpoint
    list_response = requests.request("GET", list_url, headers=headers)
    list_data = json.loads(list_response.text)

    # Check if 'sandbox' folder exists
    sandbox_id = None
    for item in list_data['value']:
        if item['name'] == 'Sandbox' and item['folder']:
            sandbox_id = item['id']
            break

    # If 'sandbox' folder doesn't exist, create it
    if sandbox_id is None:
        create_endpoint = '/drive/items/' + parent_id + '/children'
        create_url = base_url + create_endpoint
        create_payload = {
            "name": "Sandbox",
            "folder": { },
            "@mircrosoft.graph.conflictBehavior": "fail"
        }
        create_response = requests.request("POST", create_url, headers=headers, data=json.dumps(create_payload))
        print(create_response)
        create_data = json.loads(create_response.text)
        print(create_data)
        sandbox_id = create_data['id']
        
    payload = {
        "name": file_name,
        "parentReference": {
            "id": sandbox_id
        }
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code == 404:
        return jsonify("File not found")

    return jsonify(response.text)
