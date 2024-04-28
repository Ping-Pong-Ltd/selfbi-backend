from flask import Blueprint, jsonify, make_response
from flask import request, current_app as app
from flask_login import login_user, current_user, logout_user, login_required
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from core.common.variables import SERVER
from core.models import Users, Requests_Access, Role
from core import db
from datetime import datetime, timedelta, timezone
import jsonschema, jwt
import requests.exceptions


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
        
        send_email(user.id)

        return jsonify(
            {
                "message": {
                    "user": user.email,
                    "isAdmin": user.isAdmin,
                    "user_id": user.id,
                    "user_name": user.name,
                    "last_login": user.last_login,
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
    
    if not user:
        return jsonify({"message": "Register User"}), 401

    if user and check_password_hash(user.password, data["password"]):
        request_status = Requests_Access.query.filter_by(user_id=user.id).all()
        if not user.isVerified:
            return {"message": "User is not verified. Please contact the admin."} , 401
        
        for req in request_status:
            if req.status == False:
                return {"message": "Request is pending. Please wait for approval."}, 401
            

        token = generate_token(user)

        role = Role.query.get(user.role_id)
        respone = {
            "message": {
                "user": user.email,
                "isAdmin": user.isAdmin,
                "user_id": user.id,
                "user_name": user.name,
                "last_login": user.last_login,
                "access_token": token,
                "role": role.name
            }
        }

        user.last_login = db.func.now()
        db.session.commit()
        login_user(user)

        return make_response(jsonify(respone))
    else:
        return jsonify({"message": "Invalid credentials"})



@users.route("/verify_email/<token>", methods=["GET"])
def verify_email(token):
    user = Users.query.get(token)
    if user:
        user.isVerified = True
        db.session.commit()
        return jsonify({"message": "Email verified successfully"})
    




def send_email(user_id):
    try:
        user = Users.query.get(user_id)
        if user:
            user_email = user.email
            url = f"{SERVER}/send/email"
            with open("core/templates/verifyTemplate.html", "r") as file:
                html_content = file.read()
            html_content = html_content.replace("http://localhost:3000/verify_email/<token>", f"http://localhost:8080/verify_email/{user_id}")
            body = f'''{html_content}'''
            params = {
                "mail_to": user_email,
                "subject": "Project Approval Request",
                "body": body,
            }
            response = requests.request("POST", url, params=params)
            response.raise_for_status()
            return {"message": "Email sent successfully"}, 200
    except requests.exceptions.RequestException as e:
        return {"message": "Failed to send email", "error": str(e)}, 500
