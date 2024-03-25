# -*- coding: utf-8 -*-
"""
Init and user authentication in Earth Engine
"""
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser
import logging
from qgis.PyQt.QtWidgets import QMessageBox

# fix the warnings/errors messages from 'file_cache is unavailable when using oauth2client'
# https://github.com/googleapis/google-api-python-client/issues/299
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

SCOPES = [
    "https://www.googleapis.com/auth/earthengine",
    "https://www.googleapis.com/auth/devstorage.full_control",
    "https://www.googleapis.com/auth/accounts.reauth"
]

class MyHandler(BaseHTTPRequestHandler):
    """
    Listens to localhost:8085 to get the authentication code
    """
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        MyHandler.auth_code = urllib.parse.parse_qs(parsed.query)['code'][0]
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(bytes("Authentication for the QGIS Google Earth Engine plugin has been successfully completed. "
                               "You may now close this page.", 'utf-8'))

def authenticate(ee=None):
    """
    Authenticates Google Earth Engine
    """
    if ee is None:
        import ee

    # show a dialog to allow users to start or cancel the authentication process
    msg = 'This plugin uses Google Earth Engine API and it looks like it is not yet\n'\
          'authenticated on this machine. You need to have a Google account\n'\
          'registered in Google Earth Engine to continue\n\n'\
          'Click OK to open a web browser and start the authentication process\n'\
          'or click Cancel to stop the authentication process.'
    reply = QMessageBox.question(None, 'Google Earth Engine plugin',
                                 msg, QMessageBox.Ok, QMessageBox.Cancel)

    if reply == QMessageBox.Cancel:
        return False

    # start the authentication, getting user login & consent
    request_args = {
        'response_type': 'code',
        'client_id': ee.oauth.CLIENT_ID,
        'redirect_uri': "http://localhost:8085/",
        'scope': ' '.join(SCOPES),
        'access_type': 'offline'
    }
    auth_url = 'https://accounts.google.com/o/oauth2/auth/oauthchooseaccount?' \
        + urllib.parse.urlencode(request_args)
    webbrowser.open_new(auth_url)
    print('Starting Google Earth Engine Authorization ...')

    server = HTTPServer(('localhost', 8085), MyHandler)
    server.handle_request()

    if not MyHandler.auth_code:
        print('QGIS EE Plugin authentication failed, can not get authentication code')
        return False

    # get refresh token
    request_args = {
        'code': MyHandler.auth_code,
        'client_id': ee.oauth.CLIENT_ID,
        'client_secret': ee.oauth.CLIENT_SECRET,
        'redirect_uri': "http://localhost:8085/",
        'grant_type': 'authorization_code',
    }

    data = urllib.parse.urlencode(request_args).encode()
    response = urllib.request.urlopen(ee.oauth.TOKEN_URI, data).read().decode()
    refresh_token = json.loads(response)['refresh_token']

    # write refresh token
    client_info = {}
    client_info['refresh_token'] = refresh_token
    client_info['scopes'] = SCOPES
    ee.oauth.write_private_json(ee.oauth.get_credentials_path(), client_info)
    print('QGIS EE Plugin authenticated successfully')

    return True
