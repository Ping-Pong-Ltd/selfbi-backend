import json
import random

import requests
from flask import Blueprint, jsonify
from werkzeug.security import generate_password_hash

from core import db
from core.models import (
    File,
    File_Permissions_Group,
    File_Permissions_User,
    Group,
    Project,
    User_Group,
    Users,
)

populate = Blueprint("populate", __name__)


@populate.route("/populate/all")
async def populate_all():
    await populate_users()
    await populate_projects()
    await populate_files()
    await populate_groups()
    await populate_user_group()
    await populate_file_persmissions_users()
    await populate_file_persmissions_groups()
    return jsonify("All tables populated successfully!")


@populate.route("/populate/users", methods=["GET", "POST"])
def populate_users():
    data = [
        {
            "email": "admin1@example.com",
            "password": "password1",
            "isAdmin": True,
            "datetime": "2022-01-01T00:00:00Z",
        },
        {
            "email": "user4@example.com",
            "password": "password2",
            "isAdmin": False,
            "datetime": "2022-01-02T00:00:00Z",
        },
        {
            "email": "admin2@example.com",
            "password": "adminpassword",
            "isAdmin": True,
            "datetime": "2022-01-03T00:00:00Z",
        },
        {
            "email": "user1@example.com",
            "password": "userpassword1",
            "isAdmin": False,
            "datetime": "2022-01-04T00:00:00Z",
        },
        {
            "email": "user2@example.com",
            "password": "userpassword2",
            "isAdmin": False,
            "datetime": "2022-01-05T00:00:00Z",
        },
        {
            "email": "user3@example.com",
            "password": "userpassword3",
            "isAdmin": False,
            "datetime": "2022-01-06T00:00:00Z",
        },
    ]

    # Iterate over your data and add each item to the database
    for item in data:
        hash_password = generate_password_hash(item["password"])[:256]
        new_user = Users(
            email=item["email"],
            password=hash_password,
            isAdmin=item["isAdmin"],
            created_at=item["datetime"],
        )
        db.session.add(new_user)

    # Commit the changes to the database
    db.session.commit()

    return jsonify({"message": "Populated database with initial data"})


@populate.route("/popluate/projects")
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


@populate.route("/populate/files")
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
        project_id = project["id"]
        project_name = project["name"]

        # Fetch folders for the current project
        folders_response = requests.get(
            BASE_URL + FOLDERS_ENDPOINT + f"?project_name={project_name}"
        )
        folders_json = folders_response.json()

        # Check if the response is a dictionary
        if isinstance(folders_json, dict):
            folders_data = folders_json.get(project_name, [])
        else:
            folders_data = []

        # Iterate through each folder
        for folder in folders_data:
            folder_id = folder["id"]

            # Fetch files for the current folder
            files_response = requests.get(
                BASE_URL
                + FILES_ENDPOINT
                + f"?project_name={project_name}&folder_name={folder['name']}"
            )
            files_data.extend(
                [
                    {"id": file["id"], "name": file["name"], "project_id": project_id}
                    for file in files_response.json()
                ]
            )

    for file in files_data:
        new_file = File(
            id=file["id"],
            name=file["name"],
            project_id=file["project_id"],
        )
        db.session.add(new_file)

    db.session.commit()
    return jsonify("files populated successfully!")


@populate.route("/populate/groups")
async def populate_groups():
    groups_data = [
        {"name": "Group 1", "department": "IT"},
        {"name": "Group 2", "department": "HR"},
        {"name": "Group 3", "department": "Finance"},
        {"name": "Group 4", "department": "Marketing"},
    ]

    for group in groups_data:
        new_group = Group(name=group["name"], department=group["department"])
        db.session.add(new_group)

    db.session.commit()
    return jsonify("Groups populated successfully!")


@populate.route("/populate/user_group")
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


@populate.route("/populate/file_persmissions_users")
async def populate_file_persmissions_users():
    users = Users.query.all()
    files = File.query.all()

    for user in users:
        for file in files:
            permission_type = "Write" if user.isAdmin else "Read"
            file_permission = File_Permissions_User(
                file_id=file.id, user_id=user.id, permission_type=permission_type
            )
            db.session.add(file_permission)

    db.session.commit()
    return jsonify("File permissions for users populated successfully!")


@populate.route("/populate/file_persmissions_groups")
async def populate_file_persmissions_groups():
    groups = Group.query.all()
    files = File.query.all()

    for group in groups:
        for file in files:
            permission_type = "Write" if group.id % 2 == 0 else "Read"
            file_permission = File_Permissions_Group(
                file_id=file.id, group_id=group.id, permission_type=permission_type
            )
            db.session.add(file_permission)

    db.session.commit()
    return jsonify("File permissions for groups populated successfully!")
