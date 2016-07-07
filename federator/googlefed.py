#!/usr/bin/env python

from apiclient.discovery import build
import httplib2
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
import json


class GoogleApi(object):
    # we need multiple scopes, because we need to define a custom schema
    # before being able to add roles defined within that schema to a user
    scope = "https://www.googleapis.com/auth/admin.directory.user " + "https://www.googleapis.com/auth/admin.directory.userschema"

    def __init__(self, clientId=None, clientSecret=None):
        storage = Storage('credentials.dat')
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            if clientId is None or clientSecret is None:
                print("ERROR: No credentials defined. You must run init first")
                return False

            flow = OAuth2WebServerFlow(clientId, clientSecret, self.scope)
            credentials = tools.run_flow(flow, storage, tools.argparser.parse_args())

        self.http = httplib2.Http()
        self.http = credentials.authorize(self.http)
        self.service = build('admin', 'directory_v1', http=self.http)

class User(GoogleApi):
    def __init__(self, customerId=None, userKey=None, clientId=None, clientSecret=None):
        self.userKey = userKey
        super(User, self).__init__(customerId=customerId, clientId=clientId, clientSecret=clientSecret)

class Schema(GoogleApi):
    def __init__(self, customerId=None):
        super(Schema, self).__init__()
        self.customerId = customerId

    def list(self):
        request = self.service.schemas().list(customerId=self.customerId)
        response = request.execute()
        return response

    def has_sso_schema(self):
        request = self.service.schemas().list(customerId=self.customerId)
        response = request.execute()
        for schema in response['schemas']:
            if schema['schemaName'] == "SSO":
                return True

        return False

