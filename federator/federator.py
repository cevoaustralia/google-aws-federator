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
import os
import stat
import sys
from Crypto.Hash import SHA256

class Federator(object):
    # we need multiple scopes, because we need to define a custom schema
    # before being able to add roles defined within that schema to a user

    def __init__(self, clientId=None, clientSecret=None, scope=None):
        if scope is None:
            raise Exception('No scope provided')

        store = os.path.expanduser('~/.federator')
        try:
            os.mkdir(store, 0700)
        except OSError as err:
            if err.strerror != 'File exists':
                print("Cannot create credential store")
                sys.exit(1)

            # Verify the permissions
            res = os.stat(store)
            if not stat.S_ISDIR(res.st_mode):
                print("%s is not a directory" % store)
                sys.exit(1)

            if (res.st_mode & stat.S_IRWXG) or (res.st_mode & stat.S_IRWXO):
                print("Federator credentials directory %s is not safe; must be mode 0700" % store)
                sys.exit(1)

        scope_hash = SHA256.new()
        scope_hash.update(scope)
        credfile = os.path.join(store, scope_hash.hexdigest())

        # if the file exists already, make sure its permissions are safe
        try:
            res = os.stat(credfile)

            if not stat.S_ISREG(res.st_mode):
                print("Federator credentials file %s is not a regular file" % credfile)
                sys.exit(1)

            if (res.st_mode & stat.S_IRWXG) or (res.st_mode & stat.S_IRWXO) or (res.st_mode & stat.S_IXUSR):
                print("Federator credentials file %s is not safe; must be mode 0600" % credfile)
                sys.exit(1)

        except OSError as err:
            if err.errno != 2:
                raise

        storage = Storage(credfile)
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            if clientId is None or clientSecret is None:
                raise Exception("ERROR: No credentials defined. You must supply the CLIENTID and CLIENTSECRET arguments")

            flow = OAuth2WebServerFlow(clientId, clientSecret, scope)
            credentials = tools.run_flow(flow, storage, tools.argparser.parse_args())

        try:
            os.chmod(credfile, 0600)
        except:
            print("Cannot set mode of credentials file")
            raise

        self.http = httplib2.Http()
        self.http = credentials.authorize(self.http)
        self.service = build('admin', 'directory_v1', http=self.http)

class User(Federator):
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

    user_scope = "https://www.googleapis.com/auth/admin.directory.user"

    def __init__(self, userKey=None, clientId=None, clientSecret=None):
        super(User, self).__init__(scope=self.user_scope, clientId=clientId, clientSecret=clientSecret)
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



class Schema(Federator):
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

    schema_scope = "https://www.googleapis.com/auth/admin.directory.userschema"

    def __init__(self, customerId=None, clientId=None, clientSecret=None):
        super(Schema, self).__init__(scope=self.schema_scope, clientId=clientId, clientSecret=clientSecret)
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


