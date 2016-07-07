#!/usr/bin/env python

import googlefed
import sys
import argparse

def init(args):
    args = vars(args)
    googlefed.GoogleApi(clientId=args['clientid'], clientSecret=args['clientsecret'])

def schema(args):
    args = vars(args)
    schema = googlefed.Schema(customerId=args['customerid'])
    print(schema.list())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Federator", description="Manage Google Apps configurations for AWS Single Sign On")
    subparsers = parser.add_subparsers(help="subcommand help")

    parser_init = subparsers.add_parser("init", help="Initial setup of Federator")
    parser_schema = subparsers.add_parser("schema", help="Operations on custom schema")
    
    parser_init.add_argument("-I", "--clientid", required=True)
    parser_init.add_argument("-S", "--clientsecret", required=True)
    parser_init.set_defaults(func=init)

    parser_schema.add_argument("-C", "--customerid", required=True)
    parser_schema.set_defaults(func=schema)

    args = parser.parse_args()
    args.func(args)
