from flask import Blueprint, render_template, jsonify
from flask_login import login_required

home =Blueprint('home',__name__)

@home.route('/')
def home_html():
    return render_template('home.html')

@home.route('/api')
@login_required
def home_latest():
    return jsonify({'message' : 'Hello Server'})

