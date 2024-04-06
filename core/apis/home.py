from core.common.utils import token_required
from flask import Blueprint, render_template, jsonify
from flask_login import login_required

home =Blueprint('home',__name__)

@home.route('/')
def home_html():
    return render_template('home.html')

@home.route('/api')
@token_required
def home_latest(current_user):
    return jsonify({'message' : 'Hello Server'})

