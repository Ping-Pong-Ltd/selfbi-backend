from flask import Blueprint, render_template, jsonify

home =Blueprint('home',__name__)

@home.route('/')
def home_html():
    return render_template('home.html')

@home.route('/api')
def home_latest():
    return jsonify({'message' : 'Hello Server'})

