from flask import Blueprint, jsonify
from flask import request
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from core.models import Users
from core import db
import jsonschema

users = Blueprint("users", __name__)

schema = {
    "type": "object",
    "properties": {
        "email": {"type": "string", "format": "email", "maxLength": 120},
        "password": {"type": "string", "minLength": 8, "maxLength": 20},
        "datetime": {"type": "string", "format": "date-time"},
        "isAdmin": {"type": "boolean"},
    },
    "required": ["email", "password"],
}


@users.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()

    # Validate the data against the schema
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        return jsonify({"message": "Invalid data format", "error": str(e)})

    # Continue with the registration process
    try:
        hash_password = generate_password_hash(data["password"])[:256]
        new_user = Users(
            email=data["email"],
            password=hash_password,
            isAdmin=data["isAdmin"],
            created_at=data["datetime"],
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "Register"})
    except Exception as e:
        return jsonify(
            {"message": "Error occurred during registration", "error": str(e)}
        )


@users.route("/auth/login", methods=["GET", "POST"])
def login():
    data = request.get_json()

    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        return jsonify({"message": "Invalid data format", "error": str(e)})

    user = Users.query.filter_by(email=data["email"]).first()

    if user and check_password_hash(user.password, data["password"]):
        login_user(user)
        return jsonify({"message": {"user": user.email, "isAdmin": user.isAdmin}})
    else:
        return jsonify({"message": "Invalid credentials"})

@users.route("/auth/populate", methods=["GET", "POST"])
def populate_db():
    data = [
        {
            "email": "admin1@example.com",
            "password": "password1",
            "isAdmin": True,
            "datetime": "2022-01-01T00:00:00Z"
        },
        {
            "email": "user4@example.com",
            "password": "password2",
            "isAdmin": False,
            "datetime": "2022-01-02T00:00:00Z"
        },
        {
            "email": "admin2@example.com",
            "password": "adminpassword",
            "isAdmin": True,
            "datetime": "2022-01-03T00:00:00Z"
        },
        {
            "email": "user1@example.com",
            "password": "userpassword1",
            "isAdmin": False,
            "datetime": "2022-01-04T00:00:00Z"
        },
        {
            "email": "user2@example.com",
            "password": "userpassword2",
            "isAdmin": False,
            "datetime": "2022-01-05T00:00:00Z"
        },
        {
            "email": "user3@example.com",
            "password": "userpassword3",
            "isAdmin": False,
            "datetime": "2022-01-06T00:00:00Z"
        }
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