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
        file_dict = {'name': file['name'], 'cTag': file['cTag'], 'id': file['id']}
        file_dict = {'id':file_dict['id'],'cTag': file_dict['cTag'][file_dict['cTag'].index('{')+1:file_dict['cTag'].index('}')], 'name': file_dict['name']}
        print(file_dict)

    
async def copy_excel(item_id : str, new_name : str):
    
    access_token = await graph.get_app_only_token()
    payload = {}
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }
    # Get the item details
    item_endpoint = '/drive/items/' + item_id
    item_url = base_url + item_endpoint
    item_response = requests.request("GET", item_url, headers=headers)
    item_data = json.loads(item_response.text)
    print(item_data)
    

    # Get the parentReference
    parent_id = item_data['parentReference']['id']
    # print(parent_id)
    item_endpoint = '/drive/items/' + parent_id
    item_url = base_url + item_endpoint
    item_response = requests.request("GET", item_url, headers=headers)
    item_data = json.loads(item_response.text)
    print(item_data)
    
    parent_id = item_data['parentReference']['id']

    # List all items in the parent folder
    list_endpoint = '/drive/items/' + parent_id + '/children'
    list_url = base_url + list_endpoint
    list_response = requests.request("GET", list_url, headers=headers)
    list_data = json.loads(list_response.text)
    # print(list_data)

    # Check if 'sandbox' folder exists
    sandbox_id = None
    for item in list_data['value']:
        if item['name'] == 'Sandbox' and item['folder']:
            sandbox_id = item['id']
            break

    # If 'sandbox' folder doesn't exist, create it
    if sandbox_id is None:
        create_endpoint = '/drive/items/' + parent_id + '/children'
        create_url = base_url + create_endpoint
        create_payload = {
            "name": "Sandbox",
            "folder": { },
            "@mircrosoft.graph.conflictBehavior": "fail"
        }
        create_response = requests.request("POST", create_url, headers=headers, data=json.dumps(create_payload))
        print(create_response)
        create_data = json.loads(create_response.text)
        print(create_data)
        sandbox_id = create_data['id']
        
    print(sandbox_id)
    # Add the 'parentReference' to the payload
    payload = {
        "name": new_name,
        "parentReference": {
            "id": sandbox_id
        }
    }

    # Proceed with the copy operation
    endpoint = '/drive/items/' + item_id + '/copy'
    url = base_url + endpoint
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

    if response.status_code == 404:
        print('File not found')
        return

    data = json.loads(response.text)
    print(data)
    


# async def create_dashboard(dashboard_name):
#     endpoint = "/drive/root/children"
#     url = base_url + endpoint

#     access_token = await graph.get_app_only_token()
    
#     payload = {
#         "name": dashboard_name,
#         "folder": { },
#         "@microsoft.graph.conflictBehavior": "fail"
#     }
#     headers = {
#         "Authorization": "Bearer " + access_token,
#         "Content-Type": "application/json",
#     }

#     response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

#     return response

async def create_project(project_name):
    endpoint = "/drive/root:/SelfBI:/children"
    url = base_url + endpoint

    access_token = await graph.get_app_only_token()
    
    payload = {
        "name": project_name,
        "folder": { },
        "@microsoft.graph.conflictBehavior": "fail"
    }
    headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))

    return response

 
if __name__ == '__main__':
    # asyncio.run(list_excel(project_name='ExcelDashboard', folder_name='Credits'))
    # asyncio.run(copy_excel(item_id='01PWT4KLRNWRBLVH2QVRFKEXLM6STS4272', new_name='asdfef.xlsx'))
    asyncio.run(create_project('test'))
    # asyncio.run(create_dashboard('AITestDashboard'))