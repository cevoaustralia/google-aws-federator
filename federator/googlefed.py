#!/usr/bin/env python

from apiclient.discovery import build
import httplib2
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
import json
from googleapiclient.errors import HttpError

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
    rawSchema = """
    {
        "fields":
          [
            {
                "fieldName": "role",
                "fieldType": "STRING",
                "readAccessType": "ADMINS_AND_SELF",    
                "multiValued": true
            }
        ],
        "schemaName": "SSO"
    }
    """
    customSchema = json.loads(rawSchema)

    def __init__(self, customerId=None):
        super(Schema, self).__init__()
        self.customerId = customerId

    def list(self):
        request = self.service.schemas().list(customerId=self.customerId)
        response = request.execute()
        return response

    def get(self):
        key = self.customSchema['schemaName']
        request = self.service.schemas().get(customerId=self.customerId, schemaKey=key)
        response = request.execute()
        return json.dumps(response, sort_keys=True, indent=4, separators=(',', ': '))

    def exists(self):
        request = self.service.schemas().list(customerId=self.customerId)
        response = request.execute()
        for schema in response['schemas']:
            if schema['schemaName'] == "SSO":
                return True

        return False

    def create(self):
        request = self.service.schemas().insert(customerId=self.customerId, body=self.customSchema)

        try:
            response = request.execute()
        except HttpError as err:
            print(err.resp)
            if err.resp['status'] == '412':
                print("Schema already exists")
            else:
                raise

        return True

    def delete(self):
        key = self.customSchema['schemaName']
        request = self.service.schemas().delete(customerId=self.customerId, schemaKey=key)

        try:
            response = request.execute()
        except HttpError as err:
            if err.resp['status'] == '400':
                return False
            else:
                raise

        return True


