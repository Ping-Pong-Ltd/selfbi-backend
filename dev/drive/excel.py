import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import configparser
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from graph import Graph
import json
import requests

base_url = 'https://graph.microsoft.com/v1.0'

config = configparser.ConfigParser()
config.read(['../config.cfg', '../config.local.cfg'])
azure_settings = config['azure']
graph: Graph = Graph(azure_settings)

async def list_excel(project_name: str = None, folder_name: str = None):
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

    for file in data:
        file_dict = {'name': file['name'], 'cTag': file['cTag']}
        file_dict = {'cTag': file_dict['cTag'][file_dict['cTag'].index('{')+1:file_dict['cTag'].index('}')], 'name': file_dict['name']}
        print(file_dict)

        
if __name__ == '__main__':
    asyncio.run(list_excel(project_name='ExcelDashboard', folder_name='Rates'))

