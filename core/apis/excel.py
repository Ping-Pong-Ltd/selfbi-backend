import json

import requests
from flask import Blueprint, jsonify, request
# import win32com.client as win32

from core import graph, db
from core.models import File
from core.common.utils import get_download_link
from core.common.variables import SITE_ID, DRIVE_ID, MG_BASE_URL

import base64
import os
import tempfile
import shutil
from flask import send_file
from zipfile import ZipFile


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
    headers = {"Content-Type": "text/plain",
               "Authorization": "Bearer " + access_token}

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
    item_id = request.form["item_id"]
    file_name = request.form["file_name"]

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

    response = requests.request(
        "POST", url, headers=headers, data=json.dumps(payload))

    if (response.status_code == 409):
        return jsonify("File already exists")

    # print(response.headers)
    status_link = response.headers["Location"]
    status_response = requests.request("GET", status_link)
    status_data = json.loads(status_response.text)
    resource_id = status_data["resourceId"]

    project_id = db.session.query(File.project_id).filter(
        File.id == item_id).first()[0]
    
    file_data = File(
        id=resource_id,
        name=file_name,
        project_id=project_id,
        created_by=1,
    )

    db.session.add(file_data)
    db.session.commit()

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


@excel.route("/chart_data", methods=["GET"])
async def chart_data():
    item_id = request.args.get("item_id", default=None, type=str)
    worksheet_name = request.args.get("worksheet_name", default=None, type=str)

    if not (item_id or worksheet_name):
        return jsonify("Item ID and worksheet name are required")

    access_token = await graph.get_app_only_token()

    url = f"{MG_BASE_URL}/sites/{SITE_ID}/drives/{DRIVE_ID}/items/{item_id}/workbook/worksheets('{worksheet_name}')/charts"
    headers = {"Authorization": "Bearer " + access_token}

    response = requests.request("GET", url, headers=headers)

    chart_data = response.json()['value']

    # image_data = []

    # for chart in chart_data:
    #     url = f"{MG_BASE_URL}/sites/{SITE_ID}/drives/{DRIVE_ID}/items/{item_id}/workbook/worksheets('{worksheet_name}')/charts/{chart['name']}/image(width=400,height=300)"

    #     image_response = requests.request("GET", url, headers=headers)
    #     image_data.append(image_response.json())

    # return image_data

    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        for i, chart in enumerate(chart_data):
            url = f"{MG_BASE_URL}/sites/{SITE_ID}/drives/{DRIVE_ID}/items/{item_id}/workbook/worksheets('{worksheet_name}')/charts/{chart['name']}/image(width=400,height=300)"

            image_response = requests.request("GET", url, headers=headers)
            image_data = image_response.json()['value']

            # Convert base64 image data to image file
            with open(os.path.join(temp_dir, f'image_{i}.png'), 'wb') as image_file:
                image_file.write(base64.b64decode(image_data))

        # Zip the temporary directory
        shutil.make_archive(temp_dir, 'zip', temp_dir)

        # Send the zip file as a response
        return send_file(f'{temp_dir}.zip', as_attachment=True)