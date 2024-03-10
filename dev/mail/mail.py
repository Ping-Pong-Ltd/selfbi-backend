import requests
import json
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
import configparser
import asyncio
import sys
import os
import base64
import mimetypes

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph import Graph

base_url = 'https://graph.microsoft.com/v1.0'

config = configparser.ConfigParser()
config.read(['../config.cfg', '../config.local.cfg'])
azure_settings = config['azure']
graph: Graph = Graph(azure_settings)

user_id = "613af6fc-c844-4eb1-b7bf-5db0e8cd3a26"
url = f"{base_url}/users/{user_id}/sendMail"

def convert_to_base64(filepath):
    """Reads a file and returns its base64-encoded contents.

    Args:
        filename: The path to the file to be converted.

    Returns:
        A string containing the base64-encoded contents of the file.
    """

    with open(filepath, "rb") as file:
        return base64.b64encode(file.read()).decode('utf-8')

file_path = "C:/Users/sahilkamate03/Downloads/test.xlsx"
filename = "attachment.xlsx"

payload = json.dumps({
    "message": {
        "subject": "Ready for Report?",
        "body": {
            "contentType": "Text",
            "content": "Here is your report attached to the mail."
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "address": "biomolecules03@gmail.com"
                }
            }
        ],
        "attachments": [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": filename,
                "contentType": mimetypes.guess_type(file_path)[0] or "application/octet-stream",
                "contentBytes": convert_to_base64(file_path)
            }
        ]
    }
})

async def send_mail():
    access_token = await graph.get_app_only_token()


    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + access_token,
    }

    print(payload)
    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)

if __name__ == "__main__":
    asyncio.run(send_mail())