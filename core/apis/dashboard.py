import json

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
    for counter, project in enumerate(data, start=1):
        temp_dict = {"id": counter, "name": project["name"]}
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
        folders.append(folder["name"])

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
        "folder": { },
        "@microsoft.graph.conflictBehavior": "fail"
    }
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    
    return jsonify(response.json())