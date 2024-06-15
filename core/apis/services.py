import base64
import json
import mimetypes

import requests
from flask import Blueprint, jsonify, request, send_file, current_app as app

from core import graph
from core.common.utils import get_download_link, token_required
from core.common.variables import MG_BASE_URL, SERVER, USER_ID, SITE_ID, DRIVE_ID, CLIENT_URL
from core.models import Group, User_Group, Users, Requests_Access, Admin_Group, Project
from core import db
from core.common.utils import get_download_link
# from pdf2image import convert_from_path
# import win32com.client as win32
import requests
import urllib
import os
import tempfile
# import pythoncom
from collections import defaultdict


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
    response = requests.request(
        "POST", url, headers=headers, data=json.dumps(payload))

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
                existing_membership = User_Group.query.filter_by(
                    user_id=user_id, group_id=group.id).first()
                if not existing_membership:
                    user_group = User_Group(user_id=user_id, group_id=group.id)
                    db.session.add(user_group)
                    group_requests = Requests_Access.query.filter_by(
                        user_id=user_id).all()
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
        if len(granted_projects) == 0:
            body += "Already have access to the folders\n"
        else:
            # Group folders by project
            projects = defaultdict(list)
            for folder in granted_projects:
                print(f"Processing folder: {folder}")  # Debugging line
                project, folder_name = folder.split('.')
                print(f"Project: {project}, Folder: {folder_name}")  # Debugging line
                projects[project].append(folder_name)
                
            # Construct sentences
            for project, folders in projects.items():
                folders_list = ', '.join(folders)
                body += f"\n{project}: {folders_list}\n"
                
        
        replace = f"""
        \nDear User,\n
            \tWe are pleased to inform you that your access request has been approved.\n
            
            \tYou have been granted access to the following folders in the respective projects:\n
            
            {body}
            
            \tIf you already have access to the requested folders, no further action is required.\n
            
            \tPlease let us know if you have any questions or need further assistance.\n
        
        Best regards,\n
        SelfBI\n
        """
                    
        
        html_content = '''
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"> <html dir="ltr" xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="en" > <head> <meta charset="UTF-8" /> <meta content="width=device-width, initial-scale=1" name="viewport" /> <meta name="x-apple-disable-message-reformatting" /> <meta http-equiv="X-UA-Compatible" content="IE=edge" /> <meta content="telephone=no" name="format-detection" /> <title>New Template</title> <!--[if (mso 16) ]><style type="text/css"> a { text-decoration: none; } </style><! [endif]--> <!--[if gte mso 9 ]><style> sup { font-size: 100% !important; } </style><! [endif]--> <!--[if gte mso 9 ]><xml> <o:OfficeDocumentSettings> <o:AllowPNG></o:AllowPNG> <o:PixelsPerInch>96</o:PixelsPerInch> </o:OfficeDocumentSettings> </xml> <![endif]--> <style type="text/css"> .rollover:hover .rollover-first { max-height: 0px !important; display: none !important; } .rollover:hover .rollover-second { max-height: none !important; display: block !important; } .rollover span { font-size: 0px; } u + .body img ~ div div { display: none; } #outlook a { padding: 0; } span.MsoHyperlink, span.MsoHyperlinkFollowed { color: inherit; mso-style-priority: 99; } a.es-button { mso-style-priority: 100 !important; text-decoration: none !important; } a[x-apple-data-detectors] { color: inherit !important; text-decoration: none !important; font-size: inherit !important; font-family: inherit !important; font-weight: inherit !important; line-height: inherit !important; } .es-desk-hidden { display: none; float: left; overflow: hidden; width: 0; max-height: 0; line-height: 0; mso-hide: all; } .es-button-border:hover > a.es-button { color: #ffffff !important; } @media only screen and (max-width: 600px) { .es-m-p0r { padding-right: 0px !important; } .es-m-p0l { padding-left: 0px !important; } *[class="gmail-fix"] { display: none !important; } p, a { line-height: 150% !important; } h1, h1 a { line-height: 120% !important; } h2, h2 a { line-height: 120% !important; } h3, h3 a { line-height: 120% !important; } h4, h4 a { line-height: 120% !important; } h5, h5 a { line-height: 120% !important; } h6, h6 a { line-height: 120% !important; } h1 { font-size: 36px !important; text-align: left; } h2 { font-size: 26px !important; text-align: left; } h3 { font-size: 20px !important; text-align: left; } h4 { font-size: 24px !important; text-align: left; } h5 { font-size: 20px !important; text-align: left; } h6 { font-size: 16px !important; text-align: left; } .es-header-body h1 a, .es-content-body h1 a, .es-footer-body h1 a { font-size: 36px !important; } .es-header-body h2 a, .es-content-body h2 a, .es-footer-body h2 a { font-size: 26px !important; } .es-header-body h3 a, .es-content-body h3 a, .es-footer-body h3 a { font-size: 20px !important; } .es-header-body h4 a, .es-content-body h4 a, .es-footer-body h4 a { font-size: 24px !important; } .es-header-body h5 a, .es-content-body h5 a, .es-footer-body h5 a { font-size: 20px !important; } .es-header-body h6 a, .es-content-body h6 a, .es-footer-body h6 a { font-size: 16px !important; } .es-menu td a { font-size: 12px !important; } .es-header-body p, .es-header-body a { font-size: 14px !important; } .es-content-body p, .es-content-body a { font-size: 16px !important; } .es-footer-body p, .es-footer-body a { font-size: 14px !important; } .es-infoblock p, .es-infoblock a { font-size: 12px !important; } .es-m-txt-c, .es-m-txt-c h1, .es-m-txt-c h2, .es-m-txt-c h3, .es-m-txt-c h4, .es-m-txt-c h5, .es-m-txt-c h6 { text-align: center !important; } .es-m-txt-r, .es-m-txt-r h1, .es-m-txt-r h2, .es-m-txt-r h3, .es-m-txt-r h4, .es-m-txt-r h5, .es-m-txt-r h6 { text-align: right !important; } .es-m-txt-j, .es-m-txt-j h1, .es-m-txt-j h2, .es-m-txt-j h3, .es-m-txt-j h4, .es-m-txt-j h5, .es-m-txt-j h6 { text-align: justify !important; } .es-m-txt-l, .es-m-txt-l h1, .es-m-txt-l h2, .es-m-txt-l h3, .es-m-txt-l h4, .es-m-txt-l h5, .es-m-txt-l h6 { text-align: left !important; } .es-m-txt-r img, .es-m-txt-c img, .es-m-txt-l img { display: inline !important; } .es-m-txt-r .rollover:hover .rollover-second, .es-m-txt-c .rollover:hover .rollover-second, .es-m-txt-l .rollover:hover .rollover-second { display: inline !important; } .es-m-txt-r .rollover span, .es-m-txt-c .rollover span, .es-m-txt-l .rollover span { line-height: 0 !important; font-size: 0 !important; } .es-spacer { display: inline-table; } a.es-button, button.es-button { font-size: 20px !important; line-height: 120% !important; } a.es-button, button.es-button, .es-button-border { display: inline-block !important; } .es-m-fw, .es-m-fw.es-fw, .es-m-fw .es-button { display: block !important; } .es-m-il, .es-m-il .es-button, .es-social, .es-social td, .es-menu { display: inline-block !important; } .es-adaptive table, .es-left, .es-right { width: 100% !important; } .es-content table, .es-header table, .es-footer table, .es-content, .es-footer, .es-header { width: 100% !important; max-width: 600px !important; } .adapt-img { width: 100% !important; height: auto !important; } .es-mobile-hidden, .es-hidden { display: none !important; } .es-desk-hidden { width: auto !important; overflow: visible !important; float: none !important; max-height: inherit !important; line-height: inherit !important; } tr.es-desk-hidden { display: table-row !important; } table.es-desk-hidden { display: table !important; } td.es-desk-menu-hidden { display: table-cell !important; } .es-menu td { width: 1% !important; } table.es-table-not-adapt, .esd-block-html table { width: auto !important; } .es-social td { padding-bottom: 10px; } .h-auto { height: auto !important; } } @media screen and (max-width: 384px) { .mail-message-content { width: 414px !important; } } </style> </head> <body class="body" style="width: 100%; height: 100%; padding: 0; margin: 0"> <div dir="ltr" class="es-wrapper-color" lang="en" style="background-color: #fafafa" > <!--[if gte mso 9 ]><v:background xmlns:v="urn:schemas-microsoft-com:vml" fill="t"> <v:fill type="tile" color="#fafafa"></v:fill> </v:background ><![endif]--> <table class="es-wrapper" width="100%" cellspacing="0" cellpadding="0" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; padding: 0; margin: 0; width: 100%; height: 100%; background-repeat: repeat; background-position: center top; background-color: #fafafa; " > <tr> <td valign="top" style="padding: 0; margin: 0"> <table cellpadding="0" cellspacing="0" class="es-content" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; " > <tr> <td class="es-info-area" align="center" style="padding: 0; margin: 0" > <table class="es-content-body" align="center" cellpadding="0" cellspacing="0" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: transparent; width: 600px; " bgcolor="#FFFFFF" role="none" > <tr> <td align="left" style="padding: 20px; margin: 0"> <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" valign="top" style="padding: 0; margin: 0; width: 560px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" class="es-infoblock" style="padding: 0; margin: 0" > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 18px; letter-spacing: 0; color: #cccccc; font-size: 12px; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: underline; color: #cccccc; font-size: 12px; " >View online version</a > </p> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> <table cellpadding="0" cellspacing="0" class="es-header" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; background-color: transparent; background-repeat: repeat; background-position: center top; " > <tr> <td align="center" style="padding: 0; margin: 0"> <table bgcolor="#ffffff" class="es-header-body" align="center" cellpadding="0" cellspacing="0" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: transparent; width: 600px; " > <tr> <td align="left" style=" margin: 0; padding-top: 10px; padding-right: 20px; padding-bottom: 10px; padding-left: 20px; " > <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td class="es-m-p0r" valign="top" align="center" style="padding: 0; margin: 0; width: 560px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" style=" padding: 0; margin: 0; padding-bottom: 20px; font-size: 0px; " > <img src="https://ehckmhn.stripocdn.email/content/guids/CABINET_887f48b6a2f22ad4fb67bc2a58c0956b/images/93351617889024778.png" alt="Logo" style=" display: block; font-size: 12px; border: 0; outline: none; text-decoration: none; " width="200" title="Logo" height="48" /> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> <table cellpadding="0" cellspacing="0" class="es-content" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; " > <tr> <td align="center" style="padding: 0; margin: 0"> <table bgcolor="#ffffff" class="es-content-body" align="center" cellpadding="0" cellspacing="0" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: #ffffff; width: 600px; " > <tr> <td align="left" style=" margin: 0; padding-right: 20px; padding-left: 20px; padding-top: 30px; padding-bottom: 30px; " > <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" valign="top" style="padding: 0; margin: 0; width: 560px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" style=" padding: 0; margin: 0; padding-top: 10px; padding-bottom: 10px; font-size: 0px; " > <img src="https://ehckmhn.stripocdn.email/content/guids/CABINET_67e080d830d87c17802bd9b4fe1c0912/images/55191618237638326.png" alt="" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " width="100" height="72" /> </td> </tr> <tr> <td align="center" class="es-m-txt-c" style=" padding: 0; margin: 0; padding-bottom: 10px; " > <h1 style=" margin: 0; font-family: arial, 'helvetica neue', helvetica, sans-serif; mso-line-height-rule: exactly; letter-spacing: 0; font-size: 46px; font-style: normal; font-weight: bold; line-height: 46px; color: #333333; " > Project Request Approved </h1> </td> </tr> <tr> <td align="center" class="es-m-p0r es-m-p0l" style=" margin: 0; padding-top: 5px; padding-right: 40px; padding-bottom: 5px; padding-left: 40px; " > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 21px; letter-spacing: 0; color: #333333; font-size: 14px; " > [Project_data] </p> </td> </tr> <tr> <td align="center" style=" padding: 0; margin: 0; padding-top: 10px; padding-bottom: 5px; " > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 21px; letter-spacing: 0; color: #333333; font-size: 14px; " > If you did not register with us, please disregard this email. </p> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> <table cellpadding="0" cellspacing="0" class="es-footer" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; background-color: transparent; background-repeat: repeat; background-position: center top; " > <tr> <td align="center" style="padding: 0; margin: 0"> <table class="es-footer-body" align="center" cellpadding="0" cellspacing="0" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: transparent; width: 640px; " role="none" > <tr> <td align="left" style=" margin: 0; padding-right: 20px; padding-left: 20px; padding-bottom: 20px; padding-top: 20px; " > <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="left" style="padding: 0; margin: 0; width: 600px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" style=" padding: 0; margin: 0; padding-top: 15px; padding-bottom: 15px; font-size: 0; " > <table cellpadding="0" cellspacing="0" class="es-table-not-adapt es-social" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" valign="top" style=" padding: 0; margin: 0; padding-right: 40px; " > <img title="Facebook" src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/facebook-logo-black.png" alt="Fb" width="32" height="32" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " /> </td> <td align="center" valign="top" style=" padding: 0; margin: 0; padding-right: 40px; " > <img title="X.com" src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/x-logo-black.png" alt="X" width="32" height="32" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " /> </td> <td align="center" valign="top" style=" padding: 0; margin: 0; padding-right: 40px; " > <img title="Instagram" src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/instagram-logo-black.png" alt="Inst" width="32" height="32" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " /> </td> <td align="center" valign="top" style="padding: 0; margin: 0" > <img title="Youtube" src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/youtube-logo-black.png" alt="Yt" width="32" height="32" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " /> </td> </tr> </table> </td> </tr> <tr> <td align="center" style=" padding: 0; margin: 0; padding-bottom: 35px; " > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 18px; letter-spacing: 0; color: #333333; font-size: 12px; " > Style Casual&nbsp;© 2021 Style Casual, Inc. All Rights Reserved. </p> <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 18px; letter-spacing: 0; color: #333333; font-size: 12px; " > 4562 Hazy Panda Limits, Chair Crossing, Kentucky, US, 607898 </p> </td> </tr> <tr> <td style="padding: 0; margin: 0"> <table cellpadding="0" cellspacing="0" width="100%" class="es-menu" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr class="links"> <td align="center" valign="top" width="33.33%" style=" margin: 0; border: 0; padding-top: 5px; padding-bottom: 5px; padding-right: 5px; padding-left: 5px; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: none; font-family: arial, 'helvetica neue', helvetica, sans-serif; display: block; color: #999999; font-size: 12px; " >Visit Us </a> </td> <td align="center" valign="top" width="33.33%" style=" margin: 0; border: 0; padding-top: 5px; padding-bottom: 5px; padding-right: 5px; padding-left: 5px; border-left: 1px solid #cccccc; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: none; font-family: arial, 'helvetica neue', helvetica, sans-serif; display: block; color: #999999; font-size: 12px; " >Privacy Policy</a > </td> <td align="center" valign="top" width="33.33%" style=" margin: 0; border: 0; padding-top: 5px; padding-bottom: 5px; padding-right: 5px; padding-left: 5px; border-left: 1px solid #cccccc; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: none; font-family: arial, 'helvetica neue', helvetica, sans-serif; display: block; color: #999999; font-size: 12px; " >Terms of Use</a > </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> <table cellpadding="0" cellspacing="0" class="es-content" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; " > <tr> <td class="es-info-area" align="center" style="padding: 0; margin: 0" > <table class="es-content-body" align="center" cellpadding="0" cellspacing="0" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: transparent; width: 600px; " bgcolor="#FFFFFF" role="none" > <tr> <td align="left" style="padding: 20px; margin: 0"> <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" valign="top" style="padding: 0; margin: 0; width: 560px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" class="es-infoblock" style="padding: 0; margin: 0" > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 18px; letter-spacing: 0; color: #cccccc; font-size: 12px; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: underline; color: #cccccc; font-size: 12px; " ></a >No longer want to receive these emails?&nbsp;<a href="" target="_blank" style=" mso-line-height-rule: exactly; text-decoration: underline; color: #cccccc; font-size: 12px; " >Unsubscribe</a >.<a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: underline; color: #cccccc; font-size: 12px; " ></a> </p> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </div> </body> </html>
        '''
        
        html_content = html_content.replace("[Project_data]", replace)
        body = f'''{html_content}'''
        
        params = {
            "mail_to": user_email,
            "subject": "Access Granted",
            "body": body,
        }
        response = requests.request("POST", url, params=params, verify=False)

        if response.status_code == 200:
            return jsonify("User added to the group")
        else:
            return jsonify("Error sending email")

    except Exception as e:
        return jsonify(str(e))

@services.route("/request/reject", methods=["GET", "POST"])
async def mail_request_reject():
    user_id = request.args.get("user_id", default=None, type=int)

    if not user_id:
        return jsonify("User ID is required")

    

    url = f"{SERVER}/send/email"
    user_email = Users.query.get(user_id).email
    html_content = '''
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"> <html dir="ltr" xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="en" > <head> <meta charset="UTF-8" /> <meta content="width=device-width, initial-scale=1" name="viewport" /> <meta name="x-apple-disable-message-reformatting" /> <meta http-equiv="X-UA-Compatible" content="IE=edge" /> <meta content="telephone=no" name="format-detection" /> <title>New Template</title> <!--[if (mso 16) ]><style type="text/css"> a { text-decoration: none; } </style><! [endif]--> <!--[if gte mso 9 ]><style> sup { font-size: 100% !important; } </style><! [endif]--> <!--[if gte mso 9 ]><xml> <o:OfficeDocumentSettings> <o:AllowPNG></o:AllowPNG> <o:PixelsPerInch>96</o:PixelsPerInch> </o:OfficeDocumentSettings> </xml> <![endif]--> <style type="text/css"> .rollover:hover .rollover-first { max-height: 0px !important; display: none !important; } .rollover:hover .rollover-second { max-height: none !important; display: block !important; } .rollover span { font-size: 0px; } u + .body img ~ div div { display: none; } #outlook a { padding: 0; } span.MsoHyperlink, span.MsoHyperlinkFollowed { color: inherit; mso-style-priority: 99; } a.es-button { mso-style-priority: 100 !important; text-decoration: none !important; } a[x-apple-data-detectors] { color: inherit !important; text-decoration: none !important; font-size: inherit !important; font-family: inherit !important; font-weight: inherit !important; line-height: inherit !important; } .es-desk-hidden { display: none; float: left; overflow: hidden; width: 0; max-height: 0; line-height: 0; mso-hide: all; } .es-button-border:hover > a.es-button { color: #ffffff !important; } @media only screen and (max-width: 600px) { .es-m-p0r { padding-right: 0px !important; } .es-m-p0l { padding-left: 0px !important; } *[class="gmail-fix"] { display: none !important; } p, a { line-height: 150% !important; } h1, h1 a { line-height: 120% !important; } h2, h2 a { line-height: 120% !important; } h3, h3 a { line-height: 120% !important; } h4, h4 a { line-height: 120% !important; } h5, h5 a { line-height: 120% !important; } h6, h6 a { line-height: 120% !important; } h1 { font-size: 36px !important; text-align: left; } h2 { font-size: 26px !important; text-align: left; } h3 { font-size: 20px !important; text-align: left; } h4 { font-size: 24px !important; text-align: left; } h5 { font-size: 20px !important; text-align: left; } h6 { font-size: 16px !important; text-align: left; } .es-header-body h1 a, .es-content-body h1 a, .es-footer-body h1 a { font-size: 36px !important; } .es-header-body h2 a, .es-content-body h2 a, .es-footer-body h2 a { font-size: 26px !important; } .es-header-body h3 a, .es-content-body h3 a, .es-footer-body h3 a { font-size: 20px !important; } .es-header-body h4 a, .es-content-body h4 a, .es-footer-body h4 a { font-size: 24px !important; } .es-header-body h5 a, .es-content-body h5 a, .es-footer-body h5 a { font-size: 20px !important; } .es-header-body h6 a, .es-content-body h6 a, .es-footer-body h6 a { font-size: 16px !important; } .es-menu td a { font-size: 12px !important; } .es-header-body p, .es-header-body a { font-size: 14px !important; } .es-content-body p, .es-content-body a { font-size: 16px !important; } .es-footer-body p, .es-footer-body a { font-size: 14px !important; } .es-infoblock p, .es-infoblock a { font-size: 12px !important; } .es-m-txt-c, .es-m-txt-c h1, .es-m-txt-c h2, .es-m-txt-c h3, .es-m-txt-c h4, .es-m-txt-c h5, .es-m-txt-c h6 { text-align: center !important; } .es-m-txt-r, .es-m-txt-r h1, .es-m-txt-r h2, .es-m-txt-r h3, .es-m-txt-r h4, .es-m-txt-r h5, .es-m-txt-r h6 { text-align: right !important; } .es-m-txt-j, .es-m-txt-j h1, .es-m-txt-j h2, .es-m-txt-j h3, .es-m-txt-j h4, .es-m-txt-j h5, .es-m-txt-j h6 { text-align: justify !important; } .es-m-txt-l, .es-m-txt-l h1, .es-m-txt-l h2, .es-m-txt-l h3, .es-m-txt-l h4, .es-m-txt-l h5, .es-m-txt-l h6 { text-align: left !important; } .es-m-txt-r img, .es-m-txt-c img, .es-m-txt-l img { display: inline !important; } .es-m-txt-r .rollover:hover .rollover-second, .es-m-txt-c .rollover:hover .rollover-second, .es-m-txt-l .rollover:hover .rollover-second { display: inline !important; } .es-m-txt-r .rollover span, .es-m-txt-c .rollover span, .es-m-txt-l .rollover span { line-height: 0 !important; font-size: 0 !important; } .es-spacer { display: inline-table; } a.es-button, button.es-button { font-size: 20px !important; line-height: 120% !important; } a.es-button, button.es-button, .es-button-border { display: inline-block !important; } .es-m-fw, .es-m-fw.es-fw, .es-m-fw .es-button { display: block !important; } .es-m-il, .es-m-il .es-button, .es-social, .es-social td, .es-menu { display: inline-block !important; } .es-adaptive table, .es-left, .es-right { width: 100% !important; } .es-content table, .es-header table, .es-footer table, .es-content, .es-footer, .es-header { width: 100% !important; max-width: 600px !important; } .adapt-img { width: 100% !important; height: auto !important; } .es-mobile-hidden, .es-hidden { display: none !important; } .es-desk-hidden { width: auto !important; overflow: visible !important; float: none !important; max-height: inherit !important; line-height: inherit !important; } tr.es-desk-hidden { display: table-row !important; } table.es-desk-hidden { display: table !important; } td.es-desk-menu-hidden { display: table-cell !important; } .es-menu td { width: 1% !important; } table.es-table-not-adapt, .esd-block-html table { width: auto !important; } .es-social td { padding-bottom: 10px; } .h-auto { height: auto !important; } } @media screen and (max-width: 384px) { .mail-message-content { width: 414px !important; } } </style> </head> <body class="body" style="width: 100%; height: 100%; padding: 0; margin: 0"> <div dir="ltr" class="es-wrapper-color" lang="en" style="background-color: #fafafa" > <!--[if gte mso 9 ]><v:background xmlns:v="urn:schemas-microsoft-com:vml" fill="t"> <v:fill type="tile" color="#fafafa"></v:fill> </v:background ><![endif]--> <table class="es-wrapper" width="100%" cellspacing="0" cellpadding="0" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; padding: 0; margin: 0; width: 100%; height: 100%; background-repeat: repeat; background-position: center top; background-color: #fafafa; " > <tr> <td valign="top" style="padding: 0; margin: 0"> <table cellpadding="0" cellspacing="0" class="es-content" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; " > <tr> <td class="es-info-area" align="center" style="padding: 0; margin: 0" > <table class="es-content-body" align="center" cellpadding="0" cellspacing="0" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: transparent; width: 600px; " bgcolor="#FFFFFF" role="none" > <tr> <td align="left" style="padding: 20px; margin: 0"> <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" valign="top" style="padding: 0; margin: 0; width: 560px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" class="es-infoblock" style="padding: 0; margin: 0" > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 18px; letter-spacing: 0; color: #cccccc; font-size: 12px; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: underline; color: #cccccc; font-size: 12px; " >View online version</a > </p> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> <table cellpadding="0" cellspacing="0" class="es-header" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; background-color: transparent; background-repeat: repeat; background-position: center top; " > <tr> <td align="center" style="padding: 0; margin: 0"> <table bgcolor="#ffffff" class="es-header-body" align="center" cellpadding="0" cellspacing="0" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: transparent; width: 600px; " > <tr> <td align="left" style=" margin: 0; padding-top: 10px; padding-right: 20px; padding-bottom: 10px; padding-left: 20px; " > <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td class="es-m-p0r" valign="top" align="center" style="padding: 0; margin: 0; width: 560px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" style=" padding: 0; margin: 0; padding-bottom: 20px; font-size: 0px; " > <img src="https://ehckmhn.stripocdn.email/content/guids/CABINET_887f48b6a2f22ad4fb67bc2a58c0956b/images/93351617889024778.png" alt="Logo" style=" display: block; font-size: 12px; border: 0; outline: none; text-decoration: none; " width="200" title="Logo" height="48" /> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> <table cellpadding="0" cellspacing="0" class="es-content" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; " > <tr> <td align="center" style="padding: 0; margin: 0"> <table bgcolor="#ffffff" class="es-content-body" align="center" cellpadding="0" cellspacing="0" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: #ffffff; width: 600px; " > <tr> <td align="left" style=" margin: 0; padding-right: 20px; padding-left: 20px; padding-top: 30px; padding-bottom: 30px; " > <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" valign="top" style="padding: 0; margin: 0; width: 560px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" style=" padding: 0; margin: 0; padding-top: 10px; padding-bottom: 10px; font-size: 0px; " > <img src="https://ehckmhn.stripocdn.email/content/guids/CABINET_67e080d830d87c17802bd9b4fe1c0912/images/55191618237638326.png" alt="" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " width="100" height="72" /> </td> </tr> <tr> <td align="center" class="es-m-txt-c" style=" padding: 0; margin: 0; padding-bottom: 10px; " > <h1 style=" margin: 0; font-family: arial, 'helvetica neue', helvetica, sans-serif; mso-line-height-rule: exactly; letter-spacing: 0; font-size: 46px; font-style: normal; font-weight: bold; line-height: 46px; color: #333333; " > Project Request Declined </h1> </td> </tr> <tr> <td align="center" class="es-m-p0r es-m-p0l" style=" margin: 0; padding-top: 5px; padding-right: 40px; padding-bottom: 5px; padding-left: 40px; " > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 21px; letter-spacing: 0; color: #333333; font-size: 14px; " > declined_primary </p> </td> </tr> <tr> <td align="center" style=" padding: 0; margin: 0; padding-top: 10px; padding-bottom: 5px; " > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 21px; letter-spacing: 0; color: #333333; font-size: 14px; " > If you did not register with us, please disregard this email. </p> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> <table cellpadding="0" cellspacing="0" class="es-footer" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; background-color: transparent; background-repeat: repeat; background-position: center top; " > <tr> <td align="center" style="padding: 0; margin: 0"> <table class="es-footer-body" align="center" cellpadding="0" cellspacing="0" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: transparent; width: 640px; " role="none" > <tr> <td align="left" style=" margin: 0; padding-right: 20px; padding-left: 20px; padding-bottom: 20px; padding-top: 20px; " > <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="left" style="padding: 0; margin: 0; width: 600px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" style=" padding: 0; margin: 0; padding-top: 15px; padding-bottom: 15px; font-size: 0; " > <table cellpadding="0" cellspacing="0" class="es-table-not-adapt es-social" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" valign="top" style=" padding: 0; margin: 0; padding-right: 40px; " > <img title="Facebook" src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/facebook-logo-black.png" alt="Fb" width="32" height="32" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " /> </td> <td align="center" valign="top" style=" padding: 0; margin: 0; padding-right: 40px; " > <img title="X.com" src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/x-logo-black.png" alt="X" width="32" height="32" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " /> </td> <td align="center" valign="top" style=" padding: 0; margin: 0; padding-right: 40px; " > <img title="Instagram" src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/instagram-logo-black.png" alt="Inst" width="32" height="32" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " /> </td> <td align="center" valign="top" style="padding: 0; margin: 0" > <img title="Youtube" src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/youtube-logo-black.png" alt="Yt" width="32" height="32" style=" display: block; font-size: 14px; border: 0; outline: none; text-decoration: none; " /> </td> </tr> </table> </td> </tr> <tr> <td align="center" style=" padding: 0; margin: 0; padding-bottom: 35px; " > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 18px; letter-spacing: 0; color: #333333; font-size: 12px; " > Style Casual&nbsp;© 2021 Style Casual, Inc. All Rights Reserved. </p> <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 18px; letter-spacing: 0; color: #333333; font-size: 12px; " > 4562 Hazy Panda Limits, Chair Crossing, Kentucky, US, 607898 </p> </td> </tr> <tr> <td style="padding: 0; margin: 0"> <table cellpadding="0" cellspacing="0" width="100%" class="es-menu" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr class="links"> <td align="center" valign="top" width="33.33%" style=" margin: 0; border: 0; padding-top: 5px; padding-bottom: 5px; padding-right: 5px; padding-left: 5px; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: none; font-family: arial, 'helvetica neue', helvetica, sans-serif; display: block; color: #999999; font-size: 12px; " >Visit Us </a> </td> <td align="center" valign="top" width="33.33%" style=" margin: 0; border: 0; padding-top: 5px; padding-bottom: 5px; padding-right: 5px; padding-left: 5px; border-left: 1px solid #cccccc; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: none; font-family: arial, 'helvetica neue', helvetica, sans-serif; display: block; color: #999999; font-size: 12px; " >Privacy Policy</a > </td> <td align="center" valign="top" width="33.33%" style=" margin: 0; border: 0; padding-top: 5px; padding-bottom: 5px; padding-right: 5px; padding-left: 5px; border-left: 1px solid #cccccc; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: none; font-family: arial, 'helvetica neue', helvetica, sans-serif; display: block; color: #999999; font-size: 12px; " >Terms of Use</a > </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> <table cellpadding="0" cellspacing="0" class="es-content" align="center" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; width: 100%; table-layout: fixed !important; " > <tr> <td class="es-info-area" align="center" style="padding: 0; margin: 0" > <table class="es-content-body" align="center" cellpadding="0" cellspacing="0" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; background-color: transparent; width: 600px; " bgcolor="#FFFFFF" role="none" > <tr> <td align="left" style="padding: 20px; margin: 0"> <table cellpadding="0" cellspacing="0" width="100%" role="none" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" valign="top" style="padding: 0; margin: 0; width: 560px" > <table cellpadding="0" cellspacing="0" width="100%" role="presentation" style=" mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-collapse: collapse; border-spacing: 0px; " > <tr> <td align="center" class="es-infoblock" style="padding: 0; margin: 0" > <p style=" margin: 0; mso-line-height-rule: exactly; font-family: arial, 'helvetica neue', helvetica, sans-serif; line-height: 18px; letter-spacing: 0; color: #cccccc; font-size: 12px; " > <a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: underline; color: #cccccc; font-size: 12px; " ></a >No longer want to receive these emails?&nbsp;<a href="" target="_blank" style=" mso-line-height-rule: exactly; text-decoration: underline; color: #cccccc; font-size: 12px; " >Unsubscribe</a >.<a target="_blank" href="" style=" mso-line-height-rule: exactly; text-decoration: underline; color: #cccccc; font-size: 12px; " ></a> </p> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </td> </tr> </table> </div> </body> </html>
    '''


    replace = """
    \nDear User,\n

        \tThis is an automated message to inform you that your recent access request has been denied by the system administrator. Consequently, your current account has been deleted.\n

        \tTo regain access, please create a new account and submit a new access request for review.

        \tWe apologize for any inconvenience this may cause and appreciate your understanding.\n

        \tThis is a no-reply email. For further assistance, please contact our support team.\n

    Best regards,\n
    SelfBI\n
    """
    
    html_content = html_content.replace("declined_primary", replace)
    body = f'''{html_content}'''
    

    params = {
        "mail_to": user_email,
        "subject": " Access Request Denied and Account Deletion Notification",
        "body": body,
    }
    response = requests.request("POST", url, params=params, verify=False)

    if response.status_code == 200:
        # Delete related entries in the requests_access table
        db.session.query(Requests_Access).filter(Requests_Access.user_id == user_id).delete()

        # Delete the user
        db.session.query(Users).filter(Users.id == user_id).delete()
        db.session.commit()
        
        return jsonify("Email sent")
    else:
        return jsonify("Error sending email")

@services.route("/request/access", methods=["GET", "POST"])
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
        request_access = Requests_Access(
            user_id=user_id, project_id=str(project_id))
        db.session.add(request_access)
        db.session.commit()

    for project_id in project_ids:
        user_ids = [user.id for user in Admin_Group.query.filter(
            Admin_Group.project_id == project_id).all()]
        for user in Users.query.filter(Users.id.in_(user_ids)).all():
            user_emails.add(user.email)

    print(user_emails)
    url = f"{SERVER}/send/email"
    html_content = '''
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html dir="ltr" xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office" lang="en"><head><meta charset="UTF-8"><meta content="width=device-width, initial-scale=1" name="viewport"><meta name="x-apple-disable-message-reformatting"><meta http-equiv="X-UA-Compatible" content="IE=edge"><meta content="telephone=no" name="format-detection"><title>New email template 2024-04-07</title> <!--[if (mso 16)]><style type="text/css">     a {text-decoration: none;}     </style><![endif]--> <!--[if gte mso 9]><style>sup { font-size: 100% !important; }</style><![endif]--> <!--[if gte mso 9]><xml> <o:OfficeDocumentSettings> <o:AllowPNG></o:AllowPNG> <o:PixelsPerInch>96</o:PixelsPerInch> </o:OfficeDocumentSettings> </xml> <![endif]--> <!--[if !mso]><!-- --><link href="https://fonts.googleapis.com/css2?family=Imprima&display=swap" rel="stylesheet"> <!--<![endif]--><style type="text/css">.rollover:hover .rollover-first { max-height:0px!important; display:none!important; } .rollover:hover .rollover-second { max-height:none!important; display:block!important; } .rollover span { font-size:0px; } u + .body img ~ div div { display:none; } #outlook a { padding:0; } span.MsoHyperlink,span.MsoHyperlinkFollowed { color:inherit; mso-style-priority:99; } a.es-button { mso-style-priority:100!important; text-decoration:none!important; } a[x-apple-data-detectors] { color:inherit!important; text-decoration:none!important; font-size:inherit!important; font-family:inherit!important; font-weight:inherit!important; line-height:inherit!important; } .es-desk-hidden { display:none; float:left; overflow:hidden; width:0; max-height:0; line-height:0; mso-hide:all; } .es-button-border:hover > a.es-button { color:#ffffff!important; }@media only screen and (max-width:600px) {.es-m-p20b { padding-bottom:20px!important } *[class="gmail-fix"] { display:none!important } p, a { line-height:150%!important } h1, h1 a { line-height:120%!important } h2, h2 a { line-height:120%!important } h3, h3 a { line-height:120%!important } h4, h4 a { line-height:120%!important } h5, h5 a { line-height:120%!important } h6, h6 a { line-height:120%!important } h1 { font-size:30px!important; text-align:left } h2 { font-size:24px!important; text-align:left } h3 { font-size:20px!important; text-align:left } h4 { font-size:24px!important; text-align:left } h5 { font-size:20px!important; text-align:left } h6 { font-size:16px!important; text-align:left } .es-header-body h1 a, .es-content-body h1 a, .es-footer-body h1 a { font-size:30px!important } .es-header-body h2 a, .es-content-body h2 a, .es-footer-body h2 a { font-size:24px!important } .es-header-body h3 a, .es-content-body h3 a, .es-footer-body h3 a { font-size:20px!important } .es-header-body h4 a, .es-content-body h4 a, .es-footer-body h4 a { font-size:24px!important } .es-header-body h5 a, .es-content-body h5 a, .es-footer-body h5 a { font-size:20px!important } .es-header-body h6 a, .es-content-body h6 a, .es-footer-body h6 a { font-size:16px!important } .es-menu td a { font-size:14px!important } .es-header-body p, .es-header-body a { font-size:14px!important } .es-content-body p, .es-content-body a { font-size:14px!important } .es-footer-body p, .es-footer-body a { font-size:14px!important } .es-infoblock p, .es-infoblock a { font-size:12px!important } .es-m-txt-c, .es-m-txt-c h1, .es-m-txt-c h2, .es-m-txt-c h3, .es-m-txt-c h4, .es-m-txt-c h5, .es-m-txt-c h6 { text-align:center!important } .es-m-txt-r, .es-m-txt-r h1, .es-m-txt-r h2, .es-m-txt-r h3, .es-m-txt-r h4, .es-m-txt-r h5, .es-m-txt-r h6 { text-align:right!important } .es-m-txt-j, .es-m-txt-j h1, .es-m-txt-j h2, .es-m-txt-j h3, .es-m-txt-j h4, .es-m-txt-j h5, .es-m-txt-j h6 { text-align:justify!important } .es-m-txt-l, .es-m-txt-l h1, .es-m-txt-l h2, .es-m-txt-l h3, .es-m-txt-l h4, .es-m-txt-l h5, .es-m-txt-l h6 { text-align:left!important } .es-m-txt-r img, .es-m-txt-c img, .es-m-txt-l img { display:inline!important } .es-m-txt-r .rollover:hover .rollover-second, .es-m-txt-c .rollover:hover .rollover-second, .es-m-txt-l .rollover:hover .rollover-second { display:inline!important } .es-m-txt-r .rollover span, .es-m-txt-c .rollover span, .es-m-txt-l .rollover span { line-height:0!important; font-size:0!important } .es-spacer { display:inline-table } a.es-button, button.es-button { font-size:18px!important; line-height:120%!important } a.es-button, button.es-button, .es-button-border { display:block!important } .es-m-fw, .es-m-fw.es-fw, .es-m-fw .es-button { display:block!important } .es-m-il, .es-m-il .es-button, .es-social, .es-social td, .es-menu { display:inline-block!important } .es-adaptive table, .es-left, .es-right { width:100%!important } .es-content table, .es-header table, .es-footer table, .es-content, .es-footer, .es-header { width:100%!important; max-width:600px!important } .adapt-img { width:100%!important; height:auto!important } .es-mobile-hidden, .es-hidden { display:none!important } .es-desk-hidden { width:auto!important; overflow:visible!important; float:none!important; max-height:inherit!important; line-height:inherit!important } tr.es-desk-hidden { display:table-row!important } table.es-desk-hidden { display:table!important } td.es-desk-menu-hidden { display:table-cell!important } .es-menu td { width:1%!important } table.es-table-not-adapt, .esd-block-html table { width:auto!important } .es-social td { padding-bottom:10px } .h-auto { height:auto!important } a.es-button, button.es-button { border-top-width:15px!important; border-bottom-width:15px!important } }@media screen and (max-width:384px) {.mail-message-content { width:414px!important } }</style> </head> <body class="body" style="width:100%;height:100%;padding:0;Margin:0"><div dir="ltr" class="es-wrapper-color" lang="en" style="background-color:#FFFFFF"> <!--[if gte mso 9]><v:background xmlns:v="urn:schemas-microsoft-com:vml" fill="t"> <v:fill type="tile" color="#ffffff"></v:fill> </v:background><![endif]--><table class="es-wrapper" width="100%" cellspacing="0" cellpadding="0" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;padding:0;Margin:0;width:100%;height:100%;background-repeat:repeat;background-position:center top;background-color:#FFFFFF"><tr> <td valign="top" style="padding:0;Margin:0"><table cellpadding="0" cellspacing="0" class="es-footer" align="center" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important;background-color:transparent;background-repeat:repeat;background-position:center top"><tr><td align="center" style="padding:0;Margin:0"><table bgcolor="#bcb8b1" class="es-footer-body" align="center" cellpadding="0" cellspacing="0" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:600px"><tr><td align="left" style="Margin:0;padding-top:20px;padding-right:40px;padding-bottom:20px;padding-left:40px"><table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr> <td align="center" valign="top" style="padding:0;Margin:0;width:520px"><table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="center" style="padding:0;Margin:0;font-size:0px"><a target="_blank" href="http://localhost:3000/" style="mso-line-height-rule:exactly;text-decoration:underline;color:#2D3142;font-size:14px"><img src="https://ehckmhn.stripocdn.email/content/guids/CABINET_055ba03e85e991c70304fecd78a2dceaf6b3f0bc1b0eb49336463d3599679494/images/vector.png" alt="Logo" style="display:block;font-size:18px;border:0;outline:none;text-decoration:none" height="60" title="Logo" width="38"></a> </td></tr></table></td></tr></table></td></tr></table></td></tr></table> <table cellpadding="0" cellspacing="0" class="es-content" align="center" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important"><tr><td align="center" style="padding:0;Margin:0"><table bgcolor="#efefef" class="es-content-body" align="center" cellpadding="0" cellspacing="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#EFEFEF;border-radius:20px 20px 0 0;width:600px" role="none"><tr><td align="left" style="padding:0;Margin:0;padding-right:40px;padding-left:40px;padding-top:40px"><table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr> <td align="center" valign="top" style="padding:0;Margin:0;width:520px"><table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="left" class="es-m-txt-c" style="padding:0;Margin:0;font-size:0px"><a target="_blank" href="https://viewstripo.email" style="mso-line-height-rule:exactly;text-decoration:underline;color:#2D3142;font-size:18px"><img src="https://ehckmhn.stripocdn.email/content/guids/CABINET_ee77850a5a9f3068d9355050e69c76d26d58c3ea2927fa145f0d7a894e624758/images/group_4076323.png" alt="Confirm email" style="display:block;font-size:18px;border:0;outline:none;text-decoration:none;border-radius:100px" width="100" title="Confirm email" height="100"></a> </td></tr></table></td></tr></table></td></tr><tr> <td align="left" style="padding:0;Margin:0;padding-top:20px;padding-right:40px;padding-left:40px"><table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="center" valign="top" style="padding:0;Margin:0;width:520px"><table cellpadding="0" cellspacing="0" width="100%" bgcolor="#fafafa" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:separate;border-spacing:0px;background-color:#fafafa;border-radius:10px" role="presentation"><tr><td align="left" style="padding:20px;Margin:0"><h3 style="Margin:0;font-family:Imprima, Arial, sans-serif;mso-line-height-rule:exactly;letter-spacing:0;font-size:28px;font-style:normal;font-weight:bold;line-height:34px;color:#2D3142">Dear Admin,</h3> <p style="Margin:0;mso-line-height-rule:exactly;font-family:Imprima, Arial, sans-serif;line-height:27px;letter-spacing:0;color:#2D3142;font-size:18px"><br></p><p style="Margin:0;mso-line-height-rule:exactly;font-family:Imprima, Arial, sans-serif;line-height:27px;letter-spacing:0;color:#2D3142;font-size:18px">You're receiving this message because, {users_data_name} requested access on the project.<br><br>Please review the project details and click one of the buttons below:</p></td></tr></table></td></tr></table></td></tr></table></td></tr></table> <table cellpadding="0" cellspacing="0" class="es-content" align="center" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important"><tr> <td align="center" style="padding:0;Margin:0"><table bgcolor="#efefef" class="es-content-body" align="center" cellpadding="0" cellspacing="0" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#EFEFEF;width:600px"><tr><td align="left" style="padding:0;Margin:0;padding-top:20px;padding-right:40px;padding-left:40px"> <!--[if mso]><table style="width:520px" cellpadding="0" cellspacing="0"><tr><td style="width:250px" valign="top"><![endif]--><table cellpadding="0" cellspacing="0" class="es-left" align="left" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;float:left"><tr><td class="es-m-p20b" align="left" style="padding:0;Margin:0;width:250px"><table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr> <td align="center" style="padding:0;Margin:0"> <!--[if mso]><a href="http://localhost:3000/requestPage?user_id={user_id}" target="_blank" hidden> <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" esdevVmlButton href="http://localhost:3000/requestPage?user_id={user_id}" style="height:56px; v-text-anchor:middle; width:139px" arcsize="50%" stroke="f" fillcolor="#589e11"> <w:anchorlock></w:anchorlock> <center style='color:#e8e6e3; font-family:Imprima, Arial, sans-serif; font-size:22px; font-weight:700; line-height:22px; mso-text-raise:1px'>Approve</center> </v:roundrect></a> <![endif]--> <!--[if !mso]><!-- --><span class="es-button-border msohide" style="border-style:solid;border-color:#2CB543;background:#6ec615;border-width:0px;display:inline-block;border-radius:30px;width:auto;mso-hide:all"><a href="http://localhost:3000/requestPage?user_id={user_id}" class="es-button" target="_blank" style="mso-style-priority:100 !important;text-decoration:none !important;mso-line-height-rule:exactly;color:#FFFFFF;font-size:22px;padding:15px 20px 15px 20px;display:inline-block;background:#6ec615;border-radius:30px;font-family:Imprima, Arial, sans-serif;font-weight:bold;font-style:normal;line-height:26px;width:auto;text-align:center;letter-spacing:0;mso-padding-alt:0;mso-border-alt:10px solid #6ec615">Approve</a> </span> <!--<![endif]--></td></tr></table></td></tr></table> <!--[if mso]></td><td style="width:20px"></td> <td style="width:250px" valign="top"><![endif]--><table cellpadding="0" cellspacing="0" class="es-right" align="right" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;float:right"><tr><td align="left" style="padding:0;Margin:0;width:250px"><table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr> <td align="center" style="padding:0;Margin:0"> <!--[if mso]><a href="http://localhost:8080/access/reject?user_id={user_id}" target="_blank" hidden> <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" esdevVmlButton href="http://localhost:8080/access/reject?user_id={user_id}" style="height:56px; v-text-anchor:middle; width:118px" arcsize="50%" stroke="f" fillcolor="#a30000"> <w:anchorlock></w:anchorlock> <center style='color:#e8e6e3; font-family:Imprima, Arial, sans-serif; font-size:22px; font-weight:700; line-height:22px; mso-text-raise:1px'>Reject</center> </v:roundrect></a> <![endif]--> <!--[if !mso]><!-- --><span class="es-button-border msohide" style="border-style:solid;border-color:#2CB543;background:#cc0000;border-width:0px;display:inline-block;border-radius:30px;width:auto;mso-hide:all"><a href="http://localhost:8080/access/reject?user_id={user_id}" class="es-button" target="_blank" style="mso-style-priority:100 !important;text-decoration:none !important;mso-line-height-rule:exactly;color:#FFFFFF;font-size:22px;padding:15px 20px 15px 20px;display:inline-block;background:#cc0000;border-radius:30px;font-family:Imprima, Arial, sans-serif;font-weight:bold;font-style:normal;line-height:26px;width:auto;text-align:center;letter-spacing:0;mso-padding-alt:0;mso-border-alt:10px solid #cc0000">Reject</a> </span> <!--<![endif]--></td></tr></table></td></tr></table> <!--[if mso]></td></tr></table><![endif]--></td></tr><tr> <td align="left" style="padding:0;Margin:0;padding-right:40px;padding-left:40px"><table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="center" valign="top" style="padding:0;Margin:0;width:520px"><table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="left" style="padding:0;Margin:0"><p style="Margin:0;mso-line-height-rule:exactly;font-family:Imprima, Arial, sans-serif;line-height:27px;letter-spacing:0;color:#2D3142;font-size:18px">Thanks,<br>SelfBI<br type="_moz"></p></td></tr> <tr> <td align="center" style="padding:0;Margin:0;padding-bottom:20px;padding-top:40px;font-size:0"><table border="0" width="100%" height="100%" cellpadding="0" cellspacing="0" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td style="padding:0;Margin:0;border-bottom:1px solid #666666;background:unset;height:1px;width:100%;margin:0px"></td></tr></table></td></tr></table></td></tr></table></td></tr></table></td></tr></table> <table cellpadding="0" cellspacing="0" class="es-content" align="center" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important"><tr> <td align="center" style="padding:0;Margin:0"><table bgcolor="#efefef" class="es-content-body" align="center" cellpadding="0" cellspacing="0" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#EFEFEF;border-radius:0 0 20px 20px;width:600px" role="none"><tr><td class="esdev-adapt-off" align="left" style="Margin:0;padding-top:20px;padding-right:40px;padding-bottom:20px;padding-left:40px"><table cellpadding="0" cellspacing="0" class="esdev-mso-table" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:520px"><tr><td class="esdev-mso-td" valign="top" style="padding:0;Margin:0"><table cellpadding="0" cellspacing="0" align="left" class="es-left" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;float:left"><tr> <td align="center" valign="top" style="padding:0;Margin:0;width:47px"><table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="center" class="es-m-txt-l" style="padding:0;Margin:0;font-size:0px"><a target="_blank" href="https://viewstripo.email" style="mso-line-height-rule:exactly;text-decoration:underline;color:#2D3142;font-size:18px"><img src="https://ehckmhn.stripocdn.email/content/guids/CABINET_ee77850a5a9f3068d9355050e69c76d26d58c3ea2927fa145f0d7a894e624758/images/group_4076325.png" alt="Demo" style="display:block;font-size:18px;border:0;outline:none;text-decoration:none" width="47" title="Demo" height="47"></a> </td></tr></table></td></tr></table></td><td style="padding:0;Margin:0;width:20px"></td> <td class="esdev-mso-td" valign="top" style="padding:0;Margin:0"><table cellpadding="0" cellspacing="0" class="es-right" align="right" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;float:right"><tr><td align="center" valign="top" style="padding:0;Margin:0;width:453px"><table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="left" style="padding:0;Margin:0"><p style="Margin:0;mso-line-height-rule:exactly;font-family:Imprima, Arial, sans-serif;line-height:24px;letter-spacing:0;color:#2D3142;font-size:16px">This link expire in 24 hours. If you have questions, <a target="_blank" style="mso-line-height-rule:exactly;text-decoration:underline;color:#2D3142;font-size:16px" href="https://viewstripo.email">we're here to help</a></p></td></tr> </table></td></tr> </table></td></tr></table></td></tr></table></td></tr></table> <table cellpadding="0" cellspacing="0" class="es-footer" align="center" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important;background-color:transparent;background-repeat:repeat;background-position:center top"><tr><td align="center" style="padding:0;Margin:0"><table bgcolor="#bcb8b1" class="es-footer-body" align="center" cellpadding="0" cellspacing="0" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:600px"><tr><td align="left" style="Margin:0;padding-top:40px;padding-right:20px;padding-bottom:30px;padding-left:20px"><table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr> <td align="left" style="padding:0;Margin:0;width:560px"><table cellpadding="0" cellspacing="0" width="100%" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="center" class="es-m-txt-c" style="padding:0;Margin:0;padding-bottom:20px;font-size:0px"><img src="https://ehckmhn.stripocdn.email/content/guids/CABINET_055ba03e85e991c70304fecd78a2dceaf6b3f0bc1b0eb49336463d3599679494/images/vector.png" alt="Logo" style="display:block;font-size:12px;border:0;outline:none;text-decoration:none" title="Logo" height="60" width="38"></td> </tr><tr><td align="center" class="es-m-txt-c" style="padding:0;Margin:0;padding-bottom:20px;padding-top:10px;font-size:0"><table cellpadding="0" cellspacing="0" class="es-table-not-adapt es-social" role="presentation" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr> <td align="center" valign="top" style="padding:0;Margin:0;padding-right:5px"><img src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/x-logo-black.png" alt="X" title="X.com" height="24" width="24" style="display:block;font-size:18px;border:0;outline:none;text-decoration:none"></td> <td align="center" valign="top" style="padding:0;Margin:0;padding-right:5px"><img src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/facebook-logo-black.png" alt="Fb" title="Facebook" height="24" width="24" style="display:block;font-size:18px;border:0;outline:none;text-decoration:none"></td><td align="center" valign="top" style="padding:0;Margin:0"><img src="https://ehckmhn.stripocdn.email/content/assets/img/social-icons/logo-black/linkedin-logo-black.png" alt="In" title="Linkedin" height="24" width="24" style="display:block;font-size:18px;border:0;outline:none;text-decoration:none"></td></tr></table> </td></tr> <tr><td align="center" style="padding:0;Margin:0"><p style="Margin:0;mso-line-height-rule:exactly;font-family:Imprima, Arial, sans-serif;line-height:21px;letter-spacing:0;color:#2D3142;font-size:13px"><a target="_blank" style="mso-line-height-rule:exactly;text-decoration:none;color:#2D3142;font-size:14px" href=""></a><a target="_blank" style="mso-line-height-rule:exactly;text-decoration:none;color:#2D3142;font-size:14px" href="">Privacy Policy</a><a target="_blank" style="mso-line-height-rule:exactly;text-decoration:none;color:#2D3142;font-size:13px" href=""></a> • <a target="_blank" style="mso-line-height-rule:exactly;text-decoration:none;color:#2D3142;font-size:14px" href="">Unsubscribe</a></p></td></tr> <tr> <td align="center" style="padding:0;Margin:0;padding-top:20px"><p style="Margin:0;mso-line-height-rule:exactly;font-family:Imprima, Arial, sans-serif;line-height:21px;letter-spacing:0;color:#2D3142;font-size:14px">Copyright © 2024 SelfBI</p></td></tr></table></td></tr></table></td></tr></table></td></tr></table> <table cellpadding="0" cellspacing="0" class="es-footer" align="center" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;width:100%;table-layout:fixed !important;background-color:transparent;background-repeat:repeat;background-position:center top"><tr><td align="center" style="padding:0;Margin:0"><table bgcolor="#ffffff" class="es-footer-body" align="center" cellpadding="0" cellspacing="0" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px;background-color:#FFFFFF;width:600px"><tr> <td align="left" style="padding:20px;Margin:0"><table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="left" style="padding:0;Margin:0;width:560px"><table cellpadding="0" cellspacing="0" width="100%" role="none" style="mso-table-lspace:0pt;mso-table-rspace:0pt;border-collapse:collapse;border-spacing:0px"><tr><td align="center" style="padding:0;Margin:0;display:none"></td> </tr></table></td></tr></table></td></tr></table></td></tr></table></td></tr></table></div></body></html>
    '''

    html_content = html_content.replace("{users_data_name}", users_data_name)
    html_content = html_content.replace(
        "http://localhost:3000/requestPage?user_id={user_id}", f"{CLIENT_URL}/requestPage?user_id={user_id}")
    html_content = html_content.replace(
        "http://localhost:8080/access/reject?user_id={user_id}", f"{SERVER}/request/reject?user_id={user_id}")
    body = f'''{html_content}'''

    for user_email in user_emails:
        params = {
            "mail_to": user_email,
            "subject": "Project Approval Request",
            "body": body,
        }
        requests.request("POST", url, params=params, verify=False)

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
            encoded_filename = encoded_filename.replace(
                "utf-8''", "", 1)  # Remove "utf-8''"
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
    # Make a GET request to the URL
    response = requests.get(download_link, stream=True)
    headers = response.headers
    file_header = headers.get('Content-Disposition')
    extension = get_file_ext(file_header)

    with tempfile.NamedTemporaryFile(suffix=extension, dir='./core/temp/excel', delete=False) as f:
        f.write(response.content)
    output_file = tempfile.NamedTemporaryFile(suffix='.pdf').name
    image_path = excel_to_pdf(f.name, output_file, sheet_name)

    # Send the created image to the user
    return send_file(image_path, mimetype='image/png', as_attachment=True)

@services.route('/resetDB')
def reset_db():
    db.reflect()
    db.drop_all()
    db.create_all()
    return jsonify("DB Reset")

@services.route("/fullReset")
def fullReset():
    with app.test_client() as client:
        client.get('/resetDB')
        client.get('/populate/all')
    return jsonify("Full Reset Done")
