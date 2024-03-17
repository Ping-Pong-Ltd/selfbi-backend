import base64
import json
import mimetypes

import requests
from flask import Blueprint, jsonify, request

from core import graph
from core.common.utils import get_download_link
from core.common.variables import MG_BASE_URL, USER_ID

services = Blueprint("services", __name__)


def guess_mime_type(url):
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type:
        return mime_type

    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        if "Content-Type" in response.headers:
            return response.headers["Content-Type"].split(";")[0]
    except requests.RequestException as e:
        print(f"Error guessing MIME type from HTTP headers: {e}")

    return "application/octet-stream"


def convert_to_base64(filepath):
    response = requests.get(filepath)
    response.raise_for_status()
    return base64.b64encode(response.content).decode("utf-8")


@services.route("/send/email", methods=["POST"])
async def send_email():
    item_id = request.args.get("item_id", default=None, type=str)
    mail_to = request.args.get("mail_to", default=None, type=str)

    if not item_id:
        return jsonify("Item ID is required")

    if not mail_to:
        return jsonify("Mail to is required")

    file_path_url = await get_download_link(item_id)

    if not file_path_url:
        return jsonify("File not found")

    access_token = await graph.get_app_only_token()
    url = f"{MG_BASE_URL}/users/{USER_ID}/sendMail"

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + access_token,
    }

    payload = json.dumps(
        {
            "message": {
                "subject": "Excel Report",
                "body": {
                    "contentType": "Text",
                    "content": "Here is your report attached to the mail.",
                },
                "toRecipients": [{"emailAddress": {"address": mail_to}}],
                "attachments": [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": "attachment.xlsx",
                        "contentType": guess_mime_type(file_path_url),
                        "contentBytes": convert_to_base64(file_path_url),
                    }
                ],
            }
        }
    )
    response = requests.request("POST", url, headers=headers, data=payload)
    return {"status": response.status_code}


@services.route("/create/folder", methods=["POST"])
async def create_folder():
    parent_id = request.args.get("parent_id", default=None, type=str)
    folder_name = request.args.get("folder_name", default=None, type=str)
    if not parent_id:
        return jsonify("Parent ID is required")

    if not folder_name:
        return jsonify("Folder Name is required")

    access_token = await graph.get_app_only_token()

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + access_token,
    }
    create_endpoint = "/drive/items/" + parent_id + "/children"
    create_url = MG_BASE_URL + create_endpoint
    create_payload = {
        "name": folder_name,
        "folder": {},
        "@mircrosoft.graph.conflictBehavior": "fail",
    }
    create_response = requests.request(
        "POST", create_url, headers=headers, data=json.dumps(create_payload)
    )
    create_data = json.loads(create_response.text)

    return jsonify(create_data)


@services.route("/copy/file", methods=["POST"])
async def copy_file():
    item_id = request.args.get("item_id", default=None, type=str)
    parent_id = request.args.get("parent_id", default=None, type=str)
    file_name = request.args.get("file_name", default=None, type=str)
    if not item_id:
        return jsonify("Item ID is required")

    if not parent_id:
        return jsonify("Parent ID is required")

    if not file_name:
        return jsonify("File Name is required")

    access_token = await graph.get_app_only_token()

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + access_token,
    }
    url = f"{MG_BASE_URL}/drive/items/{item_id}/copy"
    payload = {
        "parentReference": {"id": parent_id},
        "name": file_name,
    }
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

    if response.status_code == 202:
        return {"message": "file saved"}

    return jsonify(response.json())
