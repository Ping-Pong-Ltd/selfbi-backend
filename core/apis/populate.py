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
    Admin_Group
)

populate = Blueprint("populate", __name__)

@populate.route("/populate/all")
async def populate_all():
    populate_users()
    await populate_projects()
    await populate_files()
    await populate_groups()
    await populate_user_group()
    populate_file_persmissions_groups()
    populate_admin_groups()
    return jsonify("All tables populated successfully!")


@populate.route("/populate/users", methods=["GET", "POST"])
def populate_users():
    data = [
        {
            "email": "realshantanurajmane@gmail.com",
            "name": "realshantanurajmane",
            "password": "password1",
            "isAdmin": True,
            "datetime": "2022-01-01T00:00:00Z",
        },
        {
            "email": "sahilkamate03@gmail.com",
            "name": "admin2",
            "password": "adminpassword",
            "isAdmin": True,
            "datetime": "2022-01-03T00:00:00Z",
        },
        {
            "email": "user4@example.com",
            "name": "user4",
            "password": "password2",
            "isAdmin": False,
            "datetime": "2022-01-02T00:00:00Z",
        },
        {
            "email": "user1@example.com",
            "name": "user1",
            "password": "userpassword1",
            "isAdmin": False,
            "datetime": "2022-01-04T00:00:00Z",
        },
        {
            "email": "user2@example.com",
            "name": "user2",
            "password": "userpassword2",
            "isAdmin": False,
            "datetime": "2022-01-05T00:00:00Z",
        },
        {
            "email": "user3@example.com",
            "name": "user3",
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
            name=item["name"],  
            password=hash_password,
            isAdmin=item["isAdmin"],
            created_at=item["datetime"],
        )
        db.session.add(new_user)

    # Commit the changes to the database
    db.session.commit()

    return jsonify({"message": "Populated database with initial data"})


@populate.route("/populate/projects")
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


def worker_to_add_file(BASE_URL, id, project_id, user_ids):
    url = f"{BASE_URL}/get_children?item_id={id}"
    response = requests.request("GET", url)
    data = response.json()
    for item in data:
        if "isFolder" not in item:
            break
        if item["isFolder"] == True:
            worker_to_add_file(BASE_URL, item["id"], project_id, user_ids)
        else:
            id = item["id"]
            name = item["name"]
            try:
                new_file = File(
                    id=id,
                    name=name,
                    project_id=project_id,
                    created_by=random.choice(user_ids),
                )
                db.session.add(new_file)

            except Exception as e:
                print(e)

    db.session.commit()


@populate.route("/populate/files")
async def populate_files():
    BASE_URL = "http://127.0.0.1:8080"
    PROJECTS_ENDPOINT = "/projects"

    projects_response = requests.get(BASE_URL + PROJECTS_ENDPOINT)
    projects_data = projects_response.json()

    users = Users.query.all()
    user_ids = [user.id for user in users]
    print(user_ids)
    for project in projects_data:
        project_id = project["id"]
        # print(project_id)
        worker_to_add_file(BASE_URL, project_id, project_id, user_ids)

    return jsonify("files populated successfully!")


@populate.route("/populate/groups")
async def populate_groups():
    groups_data = [
        {"name": "Group 1", "department": "IT"},
        {"name": "Group 2", "department": "HR"},
        {"name": "Group 3", "department": "Finance"},
        {"name": "Group 4", "department": "Marketing"},
        {"name": "Project_1.Folder_1", "department": "Admin"},
        {"name": "Project_1.Folder_2", "department": "Admin"},
        {"name": "Project_1.Folder_3", "department": "Admin"},
        {"name": "Project_2.Folder_1", "department": "Admin"},
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


def generate_random_boolean(prob_true):
    return random.random() < prob_true




@populate.route("/populate/file_persmissions_groups")
def populate_file_persmissions_groups():
    projects = Project.query.all()
    for project in projects:
        url = f"http://127.0.0.1:8080/get_children?item_id={project.id}"
        response = requests.request("GET", url)
        data = response.json()
        name_query = project.name +"."
        for item in data:
            url = f"http://127.0.0.1:8080/get_children?item_id={item["id"]}"
            response = requests.request("GET", url)
            data_file = response.json()
            if item["name"] == "Sandbox":
                continue
            temp_var = name_query + item["name"]
            group_id = Group.query.filter_by(name=temp_var).first().id
            for file in data_file:
                if "isFolder" not in file:
                    break

                file_data = File_Permissions_Group(
                    file_id=file["id"],
                    group_id=group_id,
                    permission_type="Read",
                )
                try:
                    db.session.add(file_data)
                except Exception as e:
                    print(e)
                    pass

        pass
    db.session.commit()
    return jsonify("Tested")

@populate.route("/populate/admin_groups")
def populate_admin_groups():
    data = [
        {
            "user_id": 1,
            "project_id": "01PWT4KLWBBFX6P4FNPVA2CVJNZRFMPMV4",
        },
        {
            "user_id": 2,
            "project_id": "01PWT4KLR7T7PMAKSIPJALGQEDCEF63UDJ",
        },
    ]

    for item in data:
        new_admin_group = Admin_Group(
            user_id=item["user_id"],
            project_id=item["project_id"],
        )
        db.session.add(new_admin_group)
    db.session.commit()
    return jsonify("Admin groups populated successfully!")

# @populate.route("/populate/file_persmissions_groups")
# async def populate_file_persmissions_groups():
#     groups = Group.query.all()
#     files = File.query.all()

#     for group in groups:
#         for file in files:
#             probability_true = 0.75
#             random_bool = generate_random_boolean(probability_true)
#             if random_bool:
#                 continue
#             permission_type = "Read"
#             file_permission = File_Permissions_Group(
#                 file_id=file.id, group_id=group.id, permission_type=permission_type
#             )
#             db.session.add(file_permission)

#     db.session.commit()
#     return jsonify("File permissions for groups populated successfully!")
