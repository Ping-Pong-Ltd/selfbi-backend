import base64
import json
import mimetypes

import requests
from flask import Blueprint, jsonify, request

from core import graph
from core.common.utils import get_download_link
from core.common.variables import MG_BASE_URL, SERVER, USER_ID, SITE_ID, DRIVE_ID
from core.models import Group, User_Group, Users
from core import db

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


@services.route("/send/mail/attachment", methods=["POST"])
async def send_mail_attachment():
    item_id = request.args.get("item_id", default=None, type=str)
    mail_to = request.args.get("mail_to", default=None, type=str)
    subject = request.args.get("subject", default=None, type=str)
    body = request.args.get("body", default=None, type=str)

    if not mail_to:
        return jsonify("Mail to is required")

    if not body:
        return jsonify("Body is required")

    if not subject:
        return jsonify("Subject is required")

    if not item_id:
        return jsonify("Item ID is required")

    access_token = await graph.get_app_only_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + access_token,
    }

    url = f"{MG_BASE_URL}/sites/{SITE_ID}/drives/{DRIVE_ID}/items/{item_id}"

    file_details = requests.request("GET", url, headers=headers)
    file_details = file_details.json()

    attachment_url = await get_download_link(item_id)
    attachment_url = attachment_url["Location"]

    url = f"{MG_BASE_URL}/users/{USER_ID}/sendMail"
    file_size = int(file_details["size"]) / 1048576

    payload = json.dumps(
        {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body + f"\n\nFile URL: {attachment_url}",
                },
                "toRecipients": [{"emailAddress": {"address": mail_to}}],
            }
        }
    )

    if file_size < 4:
        payload = json.dumps(
            {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "Text",
                        "content": body,
                    },
                    "toRecipients": [{"emailAddress": {"address": mail_to}}],
                    "attachments": [
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": file_details["name"],
                            "contentType": file_details["file"]["mimeType"],
                            "contentBytes": convert_to_base64(attachment_url),
                        }
                    ],
                }
            }
        )

    response = requests.request("POST", url, headers=headers, data=payload)
    return jsonify({"status": response.status_code})


@services.route("/send/email", methods=["POST"])
async def send_email():
    mail_to = request.args.get("mail_to", default=None, type=str)
    body = request.args.get("body", default=None, type=str)
    subject = request.args.get("subject", default=None, type=str)

    if not mail_to:
        return jsonify("Mail to is required")

    if not body:
        return jsonify("Body is required")

    if not subject:
        return jsonify("Subject is required")

    access_token = await graph.get_app_only_token()
    url = f"{MG_BASE_URL}/users/{USER_ID}/sendMail"

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + access_token,
    }

    payload = json.dumps(
        {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body,
                },
                "toRecipients": [{"emailAddress": {"address": mail_to}}],
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


@services.route("/mail_request/accept", methods=["POST"])
async def mail_request():
    user_id = request.args.get("user_id", default=None, type=int)
    # project_name = request.args.get("project_name", default=None, type=str)
    folder_names = request.args.get("folder_names", default=None, type=str)
    folder_names = folder_names.split(",")
    user_email = Users.query.get(user_id).email
    
    try:
        granted_projects = []
        
        for folder in folder_names:
            group = Group.query.filter_by(name=folder).first()
            if group:
                existing_membership = User_Group.query.filter_by(user_id=user_id, group_id=group.id).first()
                if not existing_membership:
                    user_group = User_Group(user_id=user_id, group_id=group.id)
                    db.session.add(user_group)
                    db.session.commit()
                    granted_projects.append(folder)
                else:
                    continue
            else:
                return jsonify("Folder not found")
            
        url = f"{SERVER}/send/email"
        body = ""
        if (len(granted_projects) == 0):
            body += f"Already have access to the folders\n"
        else:
            for folder in granted_projects:
                body += f"Access to {folder.split('/')} has been granted\n"
        params = {
            "mail_to": user_email,
            "subject": "Access Granted",
            "body": body,
        }
        response = requests.request("POST", url, params=params)
        
        if response.status_code == 200:
            return jsonify("User added to the group")
        else: 
            return jsonify("Error sending email")
        
    except Exception as e:
        return jsonify(str(e))

@services.route("/mail_request/reject", methods=["GET","POST"])
async def mail_request_reject():
    user_id = request.args.get("user_id", default=None, type=int)
    project_name = request.args.get("project_name", default=None, type=str)
    
    url = f"{SERVER}/send/email"
    user_email = Users.query.get(user_id).email
    
    body = f"Access to {project_name} has been denied"
            
    params = {
        "mail_to": user_email,
        "subject": "Access Denied",
        "body": body,
    }
    response = requests.request("POST", url, params=params)
    
    if response.status_code == 200:
        return jsonify("Email sent")
    else:
        return jsonify("Error sending email")
    