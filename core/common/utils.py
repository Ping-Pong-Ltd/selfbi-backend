import os

import requests
from dotenv import load_dotenv

from core import graph

load_dotenv(".env")
base_url = "https://graph.microsoft.com/v1.0"

drive_id = os.getenv("DRIVE_ID")


async def get_download_link(item_id, format=None):
    url = f"{base_url}/drives/{drive_id}/items/{item_id}/content?format={format}"

    access_token = await graph.get_app_only_token()

    headers = {"Authorization": "Bearer " + access_token}

    response = requests.request("GET", url, headers=headers, allow_redirects=False)

    if response.status_code == 302:
        return response.headers["Location"]

    return response.json()
