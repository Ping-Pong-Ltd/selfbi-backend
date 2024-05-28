import json

import requests
from sqlalchemy import text
from flask import Blueprint, jsonify, request

from core.models import (
    Admin_Group, 
    File, 
    Group, 
    Project, 
    Requests_Access, 
    User_Group, 
    Users
    )
from core.common.variables import DRIVE_ID, MG_BASE_URL
from core import graph, db
from core.common.utils import create_folder, token_required

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/user/projects")
@token_required
async def list_user_projects():
    user_id = request.args.get("user_id", default=None, type=str)
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
    
    project_ids = Requests_Access.query.filter_by(user_id = user_id, status = True).all()
    project_ids_array = []
    for ids in project_ids:
        project_ids_array.append(ids.project_id)
    
    response_data = []
    for project in data:
        if project["id"] in project_ids_array:
            temp_dict = {"id": project["id"], "name": project["name"]}
            response_data.append(temp_dict)
        else:
            continue

    return jsonify(response_data)

@dashboard.route("/projects")
@token_required
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

@dashboard.route("/folders")
@token_required
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
@token_required
async def list_files():
    project_name = request.args.get("project_name", default=None, type=str)
    folder_name = request.args.get("folder_name", default=None, type=str)
    project_id = request.args.get("project_id", default=None, type=str)
    user_id = request.args.get("user_id", default=None, type=str)

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

    for item in excel_file_dict:
        file_id = item["id"]
        file = File.query.get(file_id)
        if file:
            item["last_modified_by"] = file.creator.name

    if folder_name == "Sandbox":
        return jsonify(excel_file_dict)

    query = text(
        """
        SELECT DISTINCT f.id AS file_id
        FROM file f
        LEFT JOIN file_permissions_user fpu ON fpu.file_id = f.id AND fpu.user_id = :user_id
        LEFT JOIN file_permissions_group fpg ON fpg.file_id = f.id
        LEFT JOIN user_group ug ON fpg.group_id = ug.group_id AND ug.user_id = :user_id
        WHERE f.project_id = :project_id
        AND (fpu.user_id IS NOT NULL OR ug.user_id IS NOT NULL);
    """
    )

    result = db.session.execute(query, {"user_id": user_id, "project_id": project_id})
    rows = result.fetchall()
    rows = [row[0] for row in rows]

    # 'excel_file_dict' is your list of dictionaries
    excel_file_dict = [entry for entry in excel_file_dict if entry["id"] in rows]

    


    return jsonify(excel_file_dict)

@dashboard.route("/create_project", methods=["POST"])
@token_required
async def create_project():
    # Get data from request
    data = request.get_json()
    project_name = data.get("projectName")
    folders = data.get("folders")
    user_id = data.get("user_id")

    # Define endpoint and url
    endpoint = "/drive/root:/SelfBI:/children"
    url = MG_BASE_URL + endpoint

    # Get access token
    access_token = await graph.get_app_only_token()

    # Define payload and headers
    payload = {
        "name": project_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "fail",
    }
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }

    # Make request
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    parent_id = json.loads(response.text)["id"]
    
    # Create new project and add to session
    new_project = Project(id=parent_id, name=project_name)
    db.session.add(new_project)

    # Update user and create new admin group
    user = Users.query.get(user_id)
    user.isAdmin = True
    new_admin_group = Admin_Group(user_id=user_id, project_id=parent_id)
    db.session.add(new_admin_group)

    # Create folders and groups
    for folder in folders:
        folder_name = folder.get("folderName")
        await create_folder(folder_name, parent_id)
        group_name = project_name + "." + folder_name
        new_Group = Group(name=group_name, department="Admin")
        db.session.add(new_Group)
        db.session.flush()
        
        new_user_group = User_Group(user_id=user_id, group_id=new_Group.id)
        db.session.add(new_user_group)
    
    # Commit all changes to the session
    db.session.commit()
    
    return jsonify({"message": "Project and folders created successfully"}), 200


@dashboard.route("/get_children")
@token_required
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

@dashboard.route("/get_group_users")
@token_required
async def get_group_users():
    group_name = request.args.get("group_name", default=None, type=str)
    if not group_name:
        return jsonify("Group name is required")
    
    group = Group.query.filter_by(name=group_name).first()
    if not group:
        return jsonify("Group not found")
    
    users_in_group = db.session.query(Users).join(
        User_Group, Users.id == User_Group.user_id
    ).filter(User_Group.group_id == group.id).all()
    
    
    users = []
    for user in users_in_group:
        users.append({"id": user.id, "name": user.name, "email": user.email})    
    return jsonify(users)
    

    