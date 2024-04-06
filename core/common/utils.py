import requests, jwt
from functools import wraps

from core import graph
from core.models import Users
from core.common.variables import MG_BASE_URL, DRIVE_ID

from flask import jsonify, request, current_app as app

async def get_download_link(item_id, format=None):
    url = f"{MG_BASE_URL}/drives/{DRIVE_ID}/items/{item_id}/content"
    if format:
        url = f"{MG_BASE_URL}/drives/{DRIVE_ID}/items/{item_id}/content?format={format}"
    access_token = await graph.get_app_only_token()

    headers = {"Authorization": "Bearer " + access_token}

    response = requests.request("GET", url, headers=headers, allow_redirects=False)

    if response.status_code == 302:
        return response.headers

    return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # jwt is passed in the request header
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        # return 401 if token is not passed
        if not token:
            return jsonify({'message' : 'Token is missing !!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            user_id = data['public_id']
            current_user = Users.query\
                .filter_by(id = user_id)\
                .first()
            print(data)
        except Exception as e:
            print(e)
            return jsonify({
                'message' : 'Token is invalid !!'
            }), 401
        # returns the current logged in users context to the routes
        return  f(current_user, *args, **kwargs)

    return decorated