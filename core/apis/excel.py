import json

import requests
from flask import Blueprint, jsonify, request

from core import graph
from core.common.utils import get_download_link
from core.common.variables import SITE_ID, DRIVE_ID, MG_BASE_URL


excel = Blueprint("excel", __name__)


@excel.route("/upload_excel", methods=["POST"])
async def upload_excel():
    project_id = request.args.get("project_id", default=None, type=str)

    if not project_id:
        return jsonify("Project ID is required")

    relative_path = "SelfBI/{project_id}/Sandbox"
    file_name = request.args.get("file_name", default=None, type=str)
    url = f"{MG_BASE_URL}/sites/{SITE_ID}/drives/{DRIVE_ID}/root:/{relative_path}/{file_name}:/content"

    access_token = await graph.get_app_only_token()

    file = request.files["binary_file"]
    if not file:
        return jsonify("No file found")

    payload = file.read()
    headers = {"Content-Type": "text/plain", "Authorization": "Bearer " + access_token}

    response = requests.request("PUT", url, headers=headers, data=payload)

    return response.json()


@excel.route("/download_file", methods=["GET"])
async def download_file():
    item_id = request.args.get("item_id", default=None, type=str)
    format = request.args.get("format", default=None, type=str)

    if not item_id:
        return jsonify("Item ID is required")

    return str(await get_download_link(item_id, format))


@excel.route("/copy_excel", methods=["POST"])
async def copy_excel():
    item_id = request.args["item_id"]
    file_name = request.args["file_name"]

    if not (item_id or file_name):
        return jsonify("Item ID and file name are required")

    url = f"{MG_BASE_URL}/sites/{SITE_ID}/drives/{DRIVE_ID}/items/{item_id}/copy"
    if not (item_id or file_name):
        return jsonify("Item ID and file name are required")

    access_token = await graph.get_app_only_token()

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + access_token,
    }

    # Get the item details
    item_endpoint = "/drive/items/" + item_id
    item_url = MG_BASE_URL + item_endpoint
    item_response = requests.request("GET", item_url, headers=headers)
    item_data = json.loads(item_response.text)

    # Get the parentReference
    parent_id = item_data["parentReference"]["id"]

    item_endpoint = "/drive/items/" + parent_id
    item_url = MG_BASE_URL + item_endpoint
    item_response = requests.request("GET", item_url, headers=headers)
    item_data = json.loads(item_response.text)

    parent_id = item_data["parentReference"]["id"]

    # List all items in the parent folder
    list_endpoint = "/drive/items/" + parent_id + "/children"
    list_url = MG_BASE_URL + list_endpoint
    list_response = requests.request("GET", list_url, headers=headers)
    list_data = json.loads(list_response.text)

    # Check if 'sandbox' folder exists
    sandbox_id = None
    for item in list_data["value"]:
        if item["name"] == "Sandbox" and item["folder"]:
            sandbox_id = item["id"]
            break

    # If 'sandbox' folder doesn't exist, create it
    if sandbox_id is None:
        create_endpoint = "/drive/items/" + parent_id + "/children"
        create_url = MG_BASE_URL + create_endpoint
        create_payload = {
            "name": "Sandbox",
            "folder": {},
            "@mircrosoft.graph.conflictBehavior": "fail",
        }
        create_response = requests.request(
            "POST", create_url, headers=headers, data=json.dumps(create_payload)
        )
        create_data = json.loads(create_response.text)
        sandbox_id = create_data["id"]

    payload = {"parentReference": {"id": sandbox_id}, "name": file_name}

    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    if response.status_code == 404:
        return jsonify("File not found")

    msg = f"File {file_name} has been copied to the sandbox folder"

    return jsonify(msg)


@excel.route("/list_worksheets", methods=["GET"])
async def list_worksheets():
    item_id = request.args.get("item_id", default=None, type=str)

    if not item_id:
        return jsonify("Item ID is required")

    access_token = await graph.get_app_only_token()

    url = f"{MG_BASE_URL}/sites/{SITE_ID}/drives/{DRIVE_ID}/items/{item_id}/workbook/worksheets"
    headers = {"Authorization": "Bearer " + access_token}

    response = requests.request("GET", url, headers=headers)

    return response.json()['value']