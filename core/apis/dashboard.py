import json
import os

import requests
from flask import Blueprint, jsonify, request

from core import graph

dashboard = Blueprint("dashboard", __name__)

base_url = "https://graph.microsoft.com/v1.0"


@dashboard.route("/projects")
async def list_projects():
    endpoint = "/drive/root:/SelfBI:/children"

    url = base_url + endpoint

    access_token = await graph.get_app_only_token()
    payload = {}
    headers = {"Authorization": "Bearer " + access_token}

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code == 404:
        return jsonify("No Projects")

    data = json.loads(response.text)["value"]

    if not data or len(data) == 0:
        return jsonify("No projects found")

    response_data = []
    for project in data:
        temp_dict = {"id": project["id"], "name": project["name"]}
        response_data.append(temp_dict)

    return jsonify(response_data)


@dashboard.route("/folders")
async def list_folders():
    project_name = request.args.get("project_name", default=None, type=str)

    if not project_name:
        return jsonify("Project name is required")

    endpoint = "/drive/root:/SelfBI/" + project_name + ":/children"
    url = base_url + endpoint

    access_token = await graph.get_app_only_token()
    payload = {}
    headers = {"Authorization": "Bearer " + access_token}

    response = requests.request("GET", url, headers=headers, data=payload)
    if response.status_code == 404:
        return jsonify("Project not found")
    data = json.loads(response.text)["value"]

    if not data or len(data) == 0:
        return jsonify("No folders found")

    folders = []
    for folder in data:
        folders.append({"name": folder["name"], "id": folder["id"]})

    return jsonify({project_name: folders})


@dashboard.route("/files")
async def list_files():
    project_name = request.args.get("project_name", default=None, type=str)
    folder_name = request.args.get("folder_name", default=None, type=str)

    if not project_name or not folder_name:
        return jsonify("Project and folder name are required")

    endpoint = "/drive/root:/SelfBI/" + project_name + "/" + folder_name + ":/children"
    url = base_url + endpoint

    access_token = await graph.get_app_only_token()
    payload = {}
    headers = {"Authorization": "Bearer " + access_token}

    response = requests.request("GET", url, headers=headers, data=payload)
    if response.status_code == 404:
        return jsonify("Folder not found")
    data = json.loads(response.text)["value"]

    if not data or len(data) == 0:
        return jsonify("No files found")

    excel_file_dict = []
    for file in data:
        file_dict = {"name": file["name"], "cTag": file["cTag"]}
        excel_file_dict.append(
            {
                "cTag": file_dict["cTag"][
                    file_dict["cTag"].index("{") + 1 : file_dict["cTag"].index("}")
                ],
                "name": file_dict["name"],
                "created_by": file["createdBy"]["user"]["displayName"],
                "created_on": file["fileSystemInfo"]["createdDateTime"],
                "last_modified_on": file["fileSystemInfo"]["lastModifiedDateTime"],
                "last_modified_by": file["lastModifiedBy"]["user"]["displayName"],
                "id": file["id"],
            }
        )

    return jsonify(excel_file_dict)


@dashboard.route("/create_project")
async def create_project():
    project_name = request.args.get("project_name", default=None, type=str)
    endpoint = "/drive/root:/SelfBI:/children"
    url = base_url + endpoint

    access_token = await graph.get_app_only_token()

    payload = {
        "name": project_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "fail",
    }
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

    return jsonify(response.json())


@dashboard.route("/get_children")
async def get_children():
    item_id = request.args.get("item_id", default=None, type=str)
    if not item_id:
        return jsonify("Item ID is required")

    driveId = os.environ.get("DRIVE_ID")

    access_token = await graph.get_app_only_token()
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    url = base_url + f"/drives/{driveId}/items/{item_id}/children"
    response = requests.request("GET", url, headers=headers)
    if response.status_code == 404:
        return jsonify("No Files Found")
    data = json.loads(response.text)["value"]

    if not data or len(data) == 0:
        return jsonify("No folders found")

    folders = []
    for folder in data:

        folders.append(
            {
                "name": folder["name"],
                "id": folder["id"],
                "isFolder": True if "folder" in folder else False,
            }
        )

    return jsonify(folders)