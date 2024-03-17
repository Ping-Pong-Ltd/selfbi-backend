import requests
from dotenv import load_dotenv

from core import graph
from core.common.variables import MG_BASE_URL, DRIVE_ID


async def get_download_link(item_id, format=None):
    url = f"{MG_BASE_URL}/drives/{DRIVE_ID}/items/{item_id}/content"
    if format:
        url = f"{MG_BASE_URL}/drives/{DRIVE_ID}/items/{item_id}/content?format={format}"
    access_token = await graph.get_app_only_token()

    headers = {"Authorization": "Bearer " + access_token}

    response = requests.request("GET", url, headers=headers, allow_redirects=False)

    if response.status_code == 302:
        print(response.headers["Location"])
        return str(response.headers["Location"])

    return None
