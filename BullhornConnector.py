#!/usr/bin/env python3.5
"""Provides data access to the bullhorn api.
Returns the data as JSON formated text."""
import argparse
import json
import os.path
import re
import time
from urllib.parse import unquote

import requests


# The requests library is available via the PIP installer using:
# "python -m pip install requests"


def cli_args():
    """Processes and provides CLI arguments."""
    # Accept command line arguments.
    parser = argparse.ArgumentParser()
    # Add the entity command line argument.
    parser.add_argument("entity", help="Sets the entity type that the API search should use. " +
                        "E.G. 'JobSubmission'.")
    # Add the fields command line argument.
    parser.add_argument("fields",
                        help="Sets the fields of the data that should be returned with a match. " +
                        "Data should be a comma separated value " +
                        "with no space on either side of the comma. " +
                        "E.G. 'foo,bar,baz'.")
    # Add the meta data flag argument.
    parser.add_argument("-m", "--meta", help="Enable meta data output. " +
                        "This is not ELK stack friendly.", action="store_true")
    # Add the debug flag argument.
    parser.add_argument("-d", "--debug", help="Enable debugging output", action="store_true")
    # Process the arguments and make accessible
    return parser.parse_args()


class Authentication:
    """Provides the authentication strings needed for queries."""

    def __init__(self, debug=False):
        """Sets the default settings for the authentication class"""

        self.debug = debug
        self.authcode_url = 'https://auth.bullhornstaffing.com/oauth/authorize'
        self.authcode_data = {
            'client_id': '***REMOVED***',
            'response_type': 'code',
            'username': '***REMOVED***',
            'password': '***REMOVED***',
            'action': 'Login'}

        if self.debug:
            print(self.authcode_url)
            print(self.authcode_data)

    def get_authcode(self):
        """Returns the authcode.
        If no auth code is found, returns False."""

        auth_code_request = requests.get(self.authcode_url, params=self.authcode_data)
        code = re.search('(?<=code=)[0-9%a-zA-Z-]+', auth_code_request.url)

        if self.debug:
            print(auth_code_request.url)

        if code is None:
            return False
        else:
            return unquote(code.group(0))

    def get_token_data(self):
        """Returns the value of the auth token.
        If no token was found, returns false."""

        # By default a cache file does not need to be created.
        need_cache_created = False

        # Checks for the existence of the cache file.
        if os.path.isfile("token_data.json"):
            token_data_file = open("token_data.json", 'r')
            token_cache = json.loads(token_data_file.read())
            token_data_file.close()
        else:
            need_cache_created = True

        # Set the default values for the token data request.
        token_url = 'https://auth.bullhornstaffing.com/oauth/token'
        if need_cache_created:
            token_url_data = {
                'grant_type': 'authorization_code',
                'code': self.get_authcode(),
                'client_id': self.authcode_data['client_id'],
                'client_secret': '***REMOVED***'}
        else:
            token_url_data = {
                'grant_type': 'refresh_token',
                'refresh_token': token_cache["refresh_token"],
                'client_id': self.authcode_data['client_id'],
                'client_secret': '***REMOVED***'
            }

        token_request = requests.post(token_url, params=token_url_data)
        token = json.loads(token_request.text)

        # If there is no cache file then it creates one with the required data.
        if need_cache_created:
            token_data_file = open("token_data.json", 'w')
            token_data_file.write(json.dumps(token, indent=3))
            token_data_file.close()

        if self.debug:
            print(token_url)
            print(token_url_data)
            print(token_request.url)
            print(token_request.text)

        if "access_token" in token:
            return token["access_token"]
        else:
            return False


    def get_rest_access(self):
        """
        Returns the URL and token used to connect ot the rest api as a dictionary.
        The 'BhRestToken' index returns the rest API token.
        The 'restUrl' index returns the URL to access the restAPI.
        """

        # Sets the default settings for rest access authorization.
        rest_auth_url = 'https://rest.bullhornstaffing.com/rest-services/login'
        rest_auth_data = {
            'version': '*',
            'access_token': self.get_token_data()}

        rest_access_response = requests.get(rest_auth_url, params=rest_auth_data)
        rest_access = json.loads(rest_access_response.text)
        if self.debug:
            print(rest_auth_url)
            print(rest_auth_data)
            print(rest_access_response.url)
            print(rest_access)
        return rest_access


class DataAccess:
    """Returns the requested data."""

    def __init__(self, debug=False, meta=False):
        """Sets the required variables for all methods."""

        self.authenticated_rest = Authentication(debug)
        self.debug = debug
        self.rest_access = self.authenticated_rest.get_rest_access()
        self.meta_flag = meta

    def get_command(self, urlpath, command_options=None):
        """A method that allows for dynamic get commands.\n
        URL path is the argument that should be executed,\n
        E.G. restURL/entity/Department?params\n
        where entity/Department is the urlpath.\n
        Command_options takes a dictionary"""

        if command_options is None:
            command_options = {}

        get_command_params = {'BhRestToken': self.rest_access['BhRestToken']}
        get_command_params.update(command_options)

        result = requests.get(self.rest_access['restUrl'] + urlpath, params=get_command_params)

        if self.debug:
            print(command_options)
            print(get_command_params)
            print(result.url)

        return result.text

    def api_search(self, entity='JobOrder', fields='*'):
        """Runs a search command on all entries in the database.
        Returns the results of the search as JSON text."""

        # Sets the default settings for the search queries
        search_params = {
            'BhRestToken': self.rest_access['BhRestToken'],
            'query': 'dateAdded:[20140101 TO ' + time.strftime('%Y%m%d') + ']',
            'fields': fields,
            'count': 500,
            'start': 0}

        # The first query to the API using the default settings.
        search_request = requests.get(self.rest_access['restUrl'] + 'search/' + entity,
                                      params=search_params)
        # The first query is now converted to a python dictionary.
        original_search_request_parsed = json.loads(search_request.text)

        # Settings are preset for the loop:
        # Renamed the original search request, parsed to results for ease of interpretation.
        # Set the setting for the end of the loop so that the loop will end properly.
        results = original_search_request_parsed
        loop_end = original_search_request_parsed["total"] - original_search_request_parsed["count"]

        while search_params["start"] < loop_end:
            search_params["start"] = search_params["start"] + search_params["count"]
            looped_search_request = json.loads(requests.get(
                self.rest_access['restUrl'] + 'search/' + entity, params=search_params).text)
            results["data"] = results["data"] + looped_search_request["data"]

        if self.debug:
            jsonindent = 3
            print(search_params)
            print(search_request.url)
            print(original_search_request_parsed["count"])
            print(original_search_request_parsed["total"])
            #print(search_request_parsed["data"])
        else:
            jsonindent = None

        results.pop("start")
        results.pop("count")

        if self.meta_flag:
            return json.dumps(results, indent=jsonindent)
        else:
            return json.dumps(results["data"], indent=jsonindent)

if __name__ == '__main__':
    # COMMAND_LINE_ARGUMENTS = cli_args()
    # PRINTME = DataAccess(COMMAND_LINE_ARGUMENTS.debug, COMMAND_LINE_ARGUMENTS.meta)
    #fields='owner,clientCorporation,isOpen,title,submissions[0]'
    # print(PRINTME.api_search(entity=COMMAND_LINE_ARGUMENTS.entity,
    #                          fields=COMMAND_LINE_ARGUMENTS.fields))
    PRINTME = Authentication(True)
    print(PRINTME.get_token_data())
