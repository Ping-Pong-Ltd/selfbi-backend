from flask import Blueprint, jsonify, make_response
from flask import request, current_app as app
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from core.models import Users
from core import db
from datetime import datetime, timedelta, timezone
import jsonschema, jwt

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

def generate_token(user):
    token = jwt.encode({
        'public_id': user.id,
        'exp' : datetime.utcnow() + timedelta(minutes = 60)
    }, app.config['SECRET_KEY'])
    return token

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
            name=data["name"],
            password=hash_password,
            isAdmin=data["isAdmin"],
            created_at=data["datetime"],
            last_login=data["datetime"],
        )
        db.session.add(new_user)
        db.session.commit()

        user = Users.query.filter_by(email=data["email"]).first()
        token = generate_token(user)

        return jsonify(
            {
                "message": {
                    "user": user.email,
                    "isAdmin": user.isAdmin,
                    "user_id": user.id,
                    "user_name": user.name,
                    "last_login": user.last_login,
                    "access_token": token,
                }
            }
        )
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
        token = generate_token(user)

        respone = {
            "message": {
                "user": user.email,
                "isAdmin": user.isAdmin,
                "user_id": user.id,
                "user_name": user.name,
                "last_login": user.last_login,
                "access_token": token
            }
        }

        user.last_login = db.func.now()
        db.session.commit()
        return make_response(jsonify(respone))
    else:
        return jsonify({"message": "Invalid credentials"})
