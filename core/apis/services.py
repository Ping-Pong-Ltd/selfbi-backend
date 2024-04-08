import base64
import json
import mimetypes

import requests
from flask import Blueprint, jsonify, request, send_file

from core import graph
from core.common.utils import get_download_link
from core.common.variables import MG_BASE_URL, SERVER, USER_ID, SITE_ID, DRIVE_ID
from core.models import Group, User_Group, Users, Requests_Access, Admin_Group, Project
from core import db
from core.common.utils import get_download_link
from pdf2image import convert_from_path
import win32com.client as win32
import  requests, urllib, os, tempfile
import pythoncom

from sqlalchemy.orm import joinedload

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


@services.route("/request/accept", methods=["POST"])
async def mail_request():
    user_id = request.args.get("user_id", default=None, type=int)
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
                    group_requests = Requests_Access.query.filter_by(user_id=user_id).all()
                    for group_request in group_requests:
                        group_request.status = True
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

@services.route("/request/reject", methods=["GET","POST"])
async def mail_request_reject():
    user_id = request.args.get("user_id", default=None, type=int)

    if not user_id:
        return jsonify("User ID is required")

    db.session.query(Users).filter(Users.id == user_id).delete()
    db.session.commit()

    url = f"{SERVER}/send/email"
    user_email = Users.query.get(user_id).email
    
    body = f"Access to has been denied \n\nYour access request has been denied by the admin\nCreate New Account to request access again\n"
            
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
    

@services.route("/request/access", methods=["GET","POST"])
def request_access():
    user_id = request.form['user_id']
    project_ids = request.form['project_ids']
    project_ids = project_ids.split(",")
    users_data = Users.query.filter(Users.id == user_id).first()
    users_data_name = users_data.name
    if not user_id:
        return jsonify("User ID is required")
    
    if not project_ids:
        return jsonify("Project IDs are required")
    
    user_emails = set()
    for project_id in project_ids:
        request_access = Requests_Access(user_id=user_id, project_id=str(project_id))
        db.session.add(request_access)
        db.session.commit()

    for project_id in project_ids:
        user_ids = [user.id for user in Admin_Group.query.filter(Admin_Group.project_id == project_id).all()]
        for user in Users.query.filter(Users.id.in_(user_ids)).all():
            user_emails.add(user.email)
    
    print(user_emails)
    url = f"{SERVER}/send/email"
    with open("core/templates/approveMailtemplate.html", "r") as file:
        html_content = file.read()
        
    html_content = html_content.replace("{users_data_name}", users_data_name)
    html_content = html_content.replace("http://localhost:3000/requestPage?user_id={user_id}", f"http://localhost:3000/requestPage?user_id={user_id}")
    html_content = html_content.replace("http://localhost:8080/access/reject?user_id={user_id}", f"http://localhost:8080/access/reject?user_id={user_id}")
    body = f'''{html_content}'''

    for user_email in user_emails:
        params = {
            "mail_to": user_email,
            "subject": "Project Approval Request",
            "body": body,
        }
        requests.request("POST", url, params=params)

    return jsonify("Request sent")
        
@services.route("/get/requests", methods=["GET"])
def get_requests():
    user_id = request.args.get("user_id", default=None, type=int)
    if not user_id:
        return jsonify("User ID is required")
    
    # Get all requests made by the user
    user_requests = Requests_Access.query.filter_by(user_id=user_id).all()

    response_data = []

    # Loop through each request made by the user
    for req in user_requests:
        # Get the project associated with the request
        project = Project.query.filter_by(id=req.project_id).first()
        if project:
            temp = {}
            temp['name'] = project.name
            response_data.append(temp)
    
    return jsonify(response_data)


def get_file_ext(content_disposition):

    parts = content_disposition.split(";")
    for part in parts:
        if part.strip().startswith("filename*="):
            encoded_filename = part.split("filename*=", 1)[1].strip("'")
            encoded_filename = encoded_filename.replace("utf-8''", "", 1)  # Remove "utf-8''"
            filename = urllib.parse.unquote(encoded_filename)
            _, ext = os.path.splitext(filename)  # Get the file extension
            break
        elif part.strip().startswith("filename="):
            filename = part.split("filename=", 1)[1].strip("\"")
            _, ext = os.path.splitext(filename)  # Get the file extension
            break

    return ext

def pdf_to_image(pdf_path, output_folder):
    pages = convert_from_path(pdf_path)
    for page in pages:
        with tempfile.NamedTemporaryFile(suffix='.jpg', dir=output_folder, delete=False) as temp_image:
            page.save(temp_image.name, 'JPEG')
        break
    
    return temp_image.name

def excel_to_pdf(input_file, output_file, sheet_name):
    excel = win32.gencache.EnsureDispatch('Excel.Application')
    excel.Visible = False 

    try:
        wb = excel.Workbooks.Open(input_file)

        ws = wb.Worksheets(sheet_name)  

        ws.PageSetup.Zoom = False
        ws.PageSetup.FitToPagesWide = 1
        ws.PageSetup.FitToPagesTall = False

        output_file = os.path.abspath(output_file)

        ws.ExportAsFixedFormat(Type=0, Filename=output_file)
        # Type=0 is PDF, see Excel VBA documentation for other formats
        
        return pdf_to_image(output_file, './core/temp/img')

    except Exception as e:
        print(f"Failed to convert: {e}")
    finally:
        # Make sure to close the workbook and quit Excel even if an error occurred
        wb.Close(SaveChanges=False)  # No need to save changes
        excel.Quit()
        os.remove(input_file)


@services.route('/download/excel/image')
async def get_download():
    item_id = request.args.get('item_id')
    sheet_name = request.args.get('sheet_name')

    if not item_id:
        return jsonify("Item ID is required")
    
    if not sheet_name:
        return jsonify("Sheet Name is required")

    pythoncom.CoInitialize()
    download_link = await get_download_link(item_id)
    download_link = download_link['Location']
    response = requests.get(download_link, stream=True)  # Make a GET request to the URL
    headers = response.headers
    file_header = headers.get('Content-Disposition')
    extension = get_file_ext(file_header)

    with tempfile.NamedTemporaryFile(suffix=extension, dir='./core/temp/excel', delete=False) as f:
        f.write(response.content)
    output_file = tempfile.NamedTemporaryFile(suffix='.pdf').name
    image_path = excel_to_pdf(f.name, output_file, sheet_name)
    
    return  send_file(image_path, mimetype='image/png', as_attachment=True)  # Send the created image to the user