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

base_url = "https://graph.microsoft.com/v1.0"

config = configparser.ConfigParser()
config.read(["../config.cfg", "../config.local.cfg"])
azure_settings = config["azure"]
graph: Graph = Graph(azure_settings)

user_id = "613af6fc-c844-4eb1-b7bf-5db0e8cd3a26"
url = f"{base_url}/users/{user_id}/sendMail"


def guess_mime_type(url):
    # First, try to guess based on the URL extension.
    mime_type, _ = mimetypes.guess_type(url)
    if mime_type:
        return mime_type

    # If the MIME type couldn't be guessed from the URL,
    # make a HEAD request to get the headers and infer the Content-Type.
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        # Check if the Content-Type header is present and return it.
        if "Content-Type" in response.headers:
            return response.headers["Content-Type"].split(";")[
                0
            ]  # Remove charset if present.
    except requests.RequestException as e:
        print(f"Error guessing MIME type from HTTP headers: {e}")

    # Default to 'application/octet-stream' if no MIME type could be determined.
    return "application/octet-stream"


def convert_to_base64(filepath):
    """Reads a file and returns its base64-encoded contents.

    Args:
        filename: The path to the file to be converted.

    Returns:
        A string containing the base64-encoded contents of the file.
    """

    response = requests.get(filepath)
    response.raise_for_status()  # This will raise an exception for HTTP errors.
    return base64.b64encode(response.content).decode("utf-8")


file_path = "https://selfintelligence.sharepoint.com/_layouts/15/download.aspx?UniqueId=6dc21603-4f65-4bd0-842c-adbe554fb735&Translate=false&tempauth=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIwMDAwMDAwMy0wMDAwLTBmZjEtY2UwMC0wMDAwMDAwMDAwMDAvc2VsZmludGVsbGlnZW5jZS5zaGFyZXBvaW50LmNvbUAwMWFlNTdiZS05YzVhLTQxNTctOWFlYy0xY2M5NjU5YjUxZjUiLCJpc3MiOiIwMDAwMDAwMy0wMDAwLTBmZjEtY2UwMC0wMDAwMDAwMDAwMDAiLCJuYmYiOiIxNzEwNDEzNzAyIiwiZXhwIjoiMTcxMDQxNzMwMiIsImVuZHBvaW50dXJsIjoid1Z0d0lxeG1RUnlSaXlyZ09URzUwQWtoWlNyN0Q5elMzQ0RlRnZmNnVXUT0iLCJlbmRwb2ludHVybExlbmd0aCI6IjEyNyIsImlzbG9vcGJhY2siOiJUcnVlIiwiY2lkIjoiYmdBbFpzbFN0a2FtSzBTclVjOVFJZz09IiwidmVyIjoiaGFzaGVkcHJvb2Z0b2tlbiIsInNpdGVpZCI6Ik16RXpORFk0TVdRdE5Ea3lPQzAwTWpVM0xUbGhPVFF0WmpGbFpETTJaV1l5WXpCaCIsImFwcF9kaXNwbGF5bmFtZSI6IlNhaGlsIiwibmFtZWlkIjoiODFiODE1MzQtNzlhZS00ZWZhLWE1NWUtMGRmZTk0ZDQ4Yzk3QDAxYWU1N2JlLTljNWEtNDE1Ny05YWVjLTFjYzk2NTliNTFmNSIsInJvbGVzIjoic2VsZWN0ZWRzaXRlcyBncm91cC5yZWFkIGFsbHNpdGVzLnJlYWQgYWxsc2l0ZXMud3JpdGUgZ3JvdXAud3JpdGUgYWxsc2l0ZXMubWFuYWdlIGFsbGZpbGVzLndyaXRlIGFsbGZpbGVzLnJlYWQgYWxsc2l0ZXMuZnVsbGNvbnRyb2wiLCJ0dCI6IjEiLCJpcGFkZHIiOiIyMC4xOTAuMTQ1LjE3MSJ9.6zoujW2Qs9cL4TfwvpD-D2aMVAIwXQWGXJ8O7g0zMDg&ApiVersion=2.0"
filename = "attachment.xlsx"

payload = json.dumps(
    {
        "message": {
            "subject": "Ready for Report?",
            "body": {
                "contentType": "Text",
                "content": "Here is your report attached to the mail.",
            },
            "toRecipients": [{"emailAddress": {"address": "biomolecules03@gmail.com"}}],
            "attachments": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": filename,
                    "contentType": guess_mime_type(file_path),
                    "contentBytes": convert_to_base64(file_path),
                }
            ],
        }
    }
)


async def send_mail():
    access_token = await graph.get_app_only_token()

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + access_token,
    }

    print(payload)
    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)


if __name__ == "__main__":
    asyncio.run(send_mail())
