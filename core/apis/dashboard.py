import json

import requests
from flask import Blueprint, jsonify, request

from core.common.variables import DRIVE_ID, MG_BASE_URL
from core import graph

from core.models import File_Permissions_Group, File_Permissions_User, Project, File, Group, Users, User_Group
from core import db

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/projects")
async def list_projects():
    endpoint = "/drive/root:/SelfBI:/children"

    url = MG_BASE_URL + endpoint

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

@dashboard.route("/popluate_projects")
async def populate_projects():
    endpoint = "http://127.0.0.1:8080/projects"
    response = requests.request("GET", endpoint)
    data = json.loads(response.text)
    for item in data:
        new_project = Project(
            name=item["name"],
            id=item["id"],
        )
        db.session.add(new_project)
    
    db.session.commit()
    
    return jsonify("Projects populated")


@dashboard.route("/folders")
async def list_folders():
    project_name = request.args.get("project_name", default=None, type=str)

    if not project_name:
        return jsonify("Project name is required")

    endpoint = "/drive/root:/SelfBI/" + project_name + ":/children"
    url = MG_BASE_URL + endpoint

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
    url = MG_BASE_URL + endpoint

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
    url = MG_BASE_URL + endpoint

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

    access_token = await graph.get_app_only_token()
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    url = MG_BASE_URL + f"/drives/{DRIVE_ID}/items/{item_id}/children"
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


@dashboard.route("/populate_files")
async def populate_files():
    BASE_URL = "http://127.0.0.1:8080"
    PROJECTS_ENDPOINT = "/projects"
    FOLDERS_ENDPOINT = "/folders"
    FILES_ENDPOINT = "/files"
    
    projects_response = requests.get(BASE_URL + PROJECTS_ENDPOINT)
    projects_data = projects_response.json()

    files_data = []

    # Iterate through each project
    for project in projects_data:
        project_id = project['id']
        project_name = project['name']

        # Fetch folders for the current project
        folders_response = requests.get(BASE_URL + FOLDERS_ENDPOINT + f"?project_name={project_name}")
        folders_json = folders_response.json()

        # Check if the response is a dictionary
        if isinstance(folders_json, dict):
            folders_data = folders_json.get(project_name, [])
        else:
            folders_data = []

        # Iterate through each folder
        for folder in folders_data:
            folder_id = folder['id']

            # Fetch files for the current folder
            files_response = requests.get(BASE_URL + FILES_ENDPOINT + f"?project_name={project_name}&folder_name={folder['name']}")
            files_data.extend([{"id": file['id'], "name": file['name'], "project_id": project_id} for file in files_response.json()])
            
            
    for file in files_data:
        new_file = File(
            id=file["id"],
            name=file["name"],
            project_id=file["project_id"],
        )
        db.session.add(new_file)
        
    db.session.commit()
    return jsonify("files populated successfully!")


@dashboard.route("/populate_groups")
async def populate_groups():
    groups_data = [
        {"name": "Group 1", "department": "IT"},
        {"name": "Group 2", "department": "HR"},
        {"name": "Group 3", "department": "Finance"},
        {"name": "Group 4", "department": "Marketing"},
    ]

    for group in groups_data:
        new_group = Group(
            name=group['name'],
            department=group['department']
        )
        db.session.add(new_group)

    db.session.commit()
    return jsonify("Groups populated successfully!")


import random

@dashboard.route("/populate_user_group")
async def populate_user_group():
    users = Users.query.all()
    groups = Group.query.all()

    for user in users:
        if user.isAdmin:
            user_groups = groups
        else:
            # Assign only one group to the user. This can be random or a specific group.
            user_groups = [random.choice(groups[1:])]

        for group in user_groups:
            user_group = User_Group(user_id=user.id, group_id=group.id)
            db.session.add(user_group)

    db.session.commit()
    return jsonify("User groups populated successfully!")


@dashboard.route("/populate_file_persmissions_users")
async def populate_file_persmissions_users():
    users = Users.query.all()
    files = File.query.all()

    for user in users:
        for file in files:
            permission_type = "Write" if user.isAdmin else "Read"
            file_permission = File_Permissions_User(file_id=file.id, user_id=user.id, permission_type=permission_type)
            db.session.add(file_permission)

    db.session.commit()
    return jsonify("File permissions for users populated successfully!")

@dashboard.route("/populate_file_persmissions_groups")
async def populate_file_persmissions_groups():
    groups = Group.query.all()
    files = File.query.all()

    for group in groups:
        for file in files:
            permission_type = "Write" if group.id % 2 == 0 else "Read"
            file_permission = File_Permissions_Group(file_id=file.id, group_id=group.id, permission_type=permission_type)
            db.session.add(file_permission)

    db.session.commit()
    return jsonify("File permissions for groups populated successfully!")