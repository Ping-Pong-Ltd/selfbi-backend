from flask import Blueprint, jsonify, request

from msgraph.generated.models.o_data_errors.o_data_error import ODataError
import json
import requests
from core import graph


dashboard = Blueprint('dashboard', __name__)

base_url = 'https://graph.microsoft.com/v1.0'


@dashboard.route('/projects')
async def list_projects():
    endpoint = '/drive/root:/SelfBI:/children'

    url = base_url + endpoint

    access_token = await graph.get_app_only_token()
    payload = {}
    headers = {
        'Authorization': 'Bearer ' + access_token
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code == 404:
        print('No Projects')

    data = json.loads(response.text)['value']

    if not data or len(data) == 0:
        print('No projects found')
        return

    response_data = []
    for counter, project in enumerate(data, start=1):
        temp_dict = {'id': counter, 'name': project['name']}
        response_data.append(temp_dict)

    return jsonify(response_data)


@dashboard.route('/folders')
async def list_folders():
    project_name = request.args.get('project_name', default=None, type=str)

    if not project_name:
        print('Project name is required')
        return

    endpoint = '/drive/root:/SelfBI/' + project_name + ':/children'
    url = base_url + endpoint

    access_token = await graph.get_app_only_token()
    payload = {}
    headers = {
        'Authorization': 'Bearer ' + access_token
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    if response.status_code == 404:
        print('Project not found')
        return
    data = json.loads(response.text)['value']

    if not data or len(data) == 0:
        print('No folders found')
        return

    folders = []
    for folder in data:
        folders.append(folder['name'])

    return jsonify({project_name: folders})


@dashboard.route('/files')
async def list_files():
    project_name = request.args.get('project_name', default=None, type=str)
    folder_name = request.args.get('folder_name', default=None, type=str)

    if not project_name or not folder_name:
        print('Project name and folder name are required')
        return

    endpoint = '/drive/root:/SelfBI/' + \
        project_name + '/' + folder_name + ':/children'
    url = base_url + endpoint

    access_token = await graph.get_app_only_token()
    payload = {}
    headers = {
        'Authorization': 'Bearer ' + access_token
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    if response.status_code == 404:
        print('Folder not found')
        return
    data = json.loads(response.text)['value']

    if not data or len(data) == 0:
        print('No files found')
        return

    print(data)

    excel_file_dict = []
    for file in data:
        file_dict = {'name': file['name'], 'cTag': file['cTag']}
        excel_file_dict.append({
            'cTag': file_dict['cTag'][file_dict['cTag'].index('{')+1:file_dict['cTag'].index('}')], 
            'name': file_dict['name'],
            'created_by': file['createdBy']['user']['displayName'],
            'created_on' : file['fileSystemInfo']['createdDateTime'],
            'last_modified_on': file['fileSystemInfo']['lastModifiedDateTime'],
            'last_modified_by': file['lastModifiedBy']['user']['displayName'],
            'id' : file['id']
        })

    return jsonify(excel_file_dict)
