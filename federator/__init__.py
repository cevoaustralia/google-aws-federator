#!/usr/bin/env python

import federator
import sys
import argparse

def init(args):
    args = vars(args)
    federator.GoogleApi(clientId=args['clientid'], clientSecret=args['clientsecret'])

def schema_verify(args):
    args = vars(args)
    schema = federator.Schema(customerId=args['customerid'])
    if schema.exists():
        print("Custom SSO schema exists")
    else:
        print("Custom SSO schema does not exist")
        sys.exit(1)

def schema_create(args):
    args = vars(args)
    schema = federator.Schema(customerId=args['customerid'])
    if schema.exists():
        return True

    if schema.create():
        print("Created custom SSO schema")
    else:
        print("Could not create custom SSO schema")
        sys.exit(1)

def schema_delete(args):
    args = vars(args)
    schema = federator.Schema(customerId=args['customerid'])
    if not schema.exists():
        return True

    if schema.delete():
        print("Deleted custom SSO schema")
    else:
        print("Could not delete custom SSO schema -- is it in use?")
        sys.exit(1)

def schema_show(args):
    args = vars(args)
    schema = federator.Schema(customerId=args['customerid'])
    if not schema.exists():
        sys.exit(1)

    print("%s" % schema.get())

def user_add(args):
    args = vars(args)
    user = federator.User(userKey=args['userkey'])
    added = user.add_role(roleArn=args['rolearn'], providerArn=args['providerarn'])
    if added:
        print("Updated user %s" % args['userkey'])
    else:
        print("Could not add new role to user %s" % args['userkey'])
        sys.exit(1)

def user_remove(args):
    args = vars(args)
    print("removing a role from a user: %s" % args)
    user = federator.User(userKey=args['userkey'])
    if args.has_key('customtype') and args['customtype'] is not None:
        removed = user.remove_role(customType=args['customtype'])
    elif (args.has_key('rolearn') and args.has_key('providerarn')):
        removed = user.remove_role(roleArn=args['rolearn'], providerArn=args['providerarn'])
    else:
        print("You must specify either the Custom Type, or both Role and Provider ARNs")
        sys.exit(1)

    if removed:
        print("Removed role %s from user %s" % (removed, args['userkey']))
    else:
        print("Could not remove role from user %s" % args['userkey'])
        sys.exit(1)

def user_show(args):
    args = vars(args)
    user = federator.User(userKey=args['userkey'])
    print(user.get())

def main():
    parser = argparse.ArgumentParser(prog="federator", description="Manage Google Apps configurations for AWS Single Sign On")
    main_subparsers = parser.add_subparsers(help="subcommand help")

    parser_init = main_subparsers.add_parser("init", help="Initial setup of Federator")
    parser_schema = main_subparsers.add_parser("schema", help="Operations on custom schema")
    parser_user = main_subparsers.add_parser("user", help="User management")
    
    parser_init.add_argument("-I", "--clientid", required=True)
    parser_init.add_argument("-S", "--clientsecret", required=True)
    parser_init.set_defaults(func=init)

    parser_schema.add_argument("-C", "--customerid", required=True)

    schema_subparser = parser_schema.add_subparsers(help="Schema subcommand help")
    parser_schema_create = schema_subparser.add_parser("create", help="Create the custom schema")
    parser_schema_create.set_defaults(func=schema_create)

    parser_schema_delete = schema_subparser.add_parser("delete", help="Delete the custom schema")
    parser_schema_delete.set_defaults(func=schema_delete)

    parser_schema_verify = schema_subparser.add_parser("verify", help="Delete the custom schema")
    parser_schema_verify.set_defaults(func=schema_verify)

    parser_schema_show = schema_subparser.add_parser("show", help="Print the custom schema")
    parser_schema_show.set_defaults(func=schema_show)

    parser_user.add_argument("-U", "--userkey", required=True)
    user_subparser = parser_user.add_subparsers(help="User subcommand help")

    parser_user_add = user_subparser.add_parser("add", help="Add a role to a user")
    parser_user_add.add_argument("-R", "--rolearn", required=True, help="The ARN of the AWS Role")
    parser_user_add.add_argument("-P", "--providerarn", required=True, help="The ARN of the AWS Identity Provider")

    parser_user_add.set_defaults(func=user_add)

    parser_user_remove = user_subparser.add_parser("remove", help="Remove a role from a user. You must specify either the custom type name, or both the role/provider ARNs")
    parser_user_remove.add_argument("-R", "--rolearn", help="The ARN of the AWS Role to remove")
    parser_user_remove.add_argument("-P", "--providerarn", help="The ARN of the AWS Identity Provider associated with the role to remove")
    parser_user_remove.add_argument("-T", "--customtype", help="The custom Type name of the role to remove")

    parser_user_remove.set_defaults(func=user_remove)

    parser_user_show = user_subparser.add_parser("show", help="Show the current shape of a user")
    parser_user_show.set_defaults(func=user_show)

    args = parser.parse_args()
    # have to clean out our command-line args or they get swallowed twice during init
    sys.argv = ['']
    args.func(args)

if __name__ == "__main__":
    main()
