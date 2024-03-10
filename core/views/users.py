from flask import Blueprint, jsonify
from flask import request
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from core.models import User
from core import db
import jsonschema

users = Blueprint('users', __name__)

schema = {
    "type": "object",
    "properties": {
        "email": {"type": "string", "format": "email", "maxLength": 120},
        "password": {"type": "string", "minLength": 8, "maxLength": 20}
    },
    "required": ["email", "password"]
}

@users.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    # Validate the data against the schema
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        return jsonify({'message': 'Invalid data format', 'error': str(e)})

    # Continue with the registration process
    hash_password = generate_password_hash(data['password'])[:256]
    new_user = User(email=data['email'], password=hash_password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'Register'})

@users.route('/auth/login', methods=['GET','POST'])
def login():
    data = request.get_json()
    
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        return jsonify({'message': 'Invalid data format', 'error': str(e)})
    
    user = User.query.filter_by(email=data['email']).first()
    
    if user and check_password_hash(user.password, data['password']):
        login_user(user)
        return jsonify({'message': 'Login'})
    else:
        return jsonify({'message': 'Invalid credentials'})