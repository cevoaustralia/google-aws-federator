#!/usr/bin/env python

from apiclient.discovery import build
import httplib2
from oauth2client import tools
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
import json
from googleapiclient.errors import HttpError
import re

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
    roleArnShape = re.compile('^arn:aws:iam::(\d{12}):role/(\w+)')
    providerArnShape = re.compile('^arn:aws:iam::\d{12}:saml-provider/\w+')

    patchShape = """
    {
        "customSchemas": {
            "SSO": {
                "role": [
                    {
                        "value": "%s,%s",
                        "customType": "%s"
                    }
                ]
            }
        }
    }
    """

    def __init__(self, userKey=None):
        super(User, self).__init__()
        self.userKey = userKey

    def get(self):
        request = self.service.users().get(userKey=self.userKey, projection='full')
        return json.dumps(request.execute(), sort_keys=True, indent=4, separators=(',', ': '))

    def add_role(self, roleArn=None, providerArn=None):
        # Make sure the ARNs are the right kind of shape
        roleMatch = self.roleArnShape.match(roleArn)
        if not roleMatch:
            print("Role ARN is incorrect; must be 'arn:aws:iam::<ACCOUNTID>:role/<SOMETHING>'")
            return False

        providerMatch = self.providerArnShape.match(providerArn)
        if not providerMatch:
            print("Provider ARN is incorrect; must be 'arn:aws:iam::<ACCOUNTID>:saml-provider/<SOMETHING>'")
            return False

        # We have to _add_ the patch to the existing set,
        # because the whole custom schema is replaced. We will only add it if the 
        # <rolearn>,<providerarn> tuple is different and if the customType name
        # is different. This means that we can't, for example, have two roles
        # with the same name in the same account but with different SAML providers, but
        # I think that's OK because I don't think AWS lets you do that anyhow
        current = json.loads(self.get())
        if current.has_key('customSchemas') and current['customSchemas'].has_key('SSO'):
            current = current['customSchemas']['SSO']
        else:
            current = {'role':[]}

        typeName = roleMatch.group(1) + '-' + roleMatch.group(2)
        shape = self.patchShape % (roleArn, providerArn, typeName)
        patch = json.loads(shape)

        do_add = True
        for role in current['role']:
            if role['value'] == roleArn + "," + providerArn:
                do_add = False
                continue

            if role['customType'] == typeName:
                do_add = False
                continue

            patch['customSchemas']['SSO']['role'].append(role)

        if not do_add:
            print("That user already has access to that role")
            return True

        request = self.service.users().patch(userKey=self.userKey, body=patch)
        response = request.execute()
        return roleMatch.group(2)

    def remove_role(self, roleArn=None, providerArn=None, customType=None):
        if roleArn is None and providerArn is None and customType is None:
            print("ERROR: You must specify the Role ARN and the Provider ARN, or the Custom Type")
            return False

        # Removing a role is similar to adding one -- we need to update the current
        # custom schema set and re-patch the user.
        current = json.loads(self.get())
        if current.has_key('customSchemas') and current['customSchemas'].has_key('SSO'):
            current = current['customSchemas']['SSO']
        else:
            # there are no custom roles associated
            return "user has no roles"

        new_shape = {
            'customSchemas': {
                'SSO': {
                    'role': []
                }
            }
        }

        removed = None
        for role in current['role']:
            # copy all the roles across to the new list, unless it matches the one
            # that we're removing
            if customType:
                if role['customType'] == customType:
                    removed = customType
                    continue
            elif roleArn and providerArn:
                value = roleArn + "," + providerArn
                if role['value'] == value:
                    removed = value
                    continue
            else:
                print("I don't know how I got here")
                sys.exit(1)

            new_shape['customSchemas']['SSO']['role'].append(role)

        if removed:
            request = self.service.users().patch(userKey=self.userKey, body=new_shape)
            response = request.execute()

        return removed



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


