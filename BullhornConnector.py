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

    # init function to be executed when the class is instantiated so that
    # various variables are not missing at method call time.
    def __init__(self, debug=False):
        """Sets the default settings for the authentication class"""

        # Set the initial values for the Authentication class
        self.debug = debug
        self.credentials = {
            'client_id': '***REMOVED***',
            'client_secret': '***REMOVED***',
            'username': '***REMOVED***',
            'password': '***REMOVED***'}

        # If debugging is enabled then print debug values.
        if self.debug:
            print(self.credentials)

    def get_authcode(self):
        """Returns the authcode.
        If no auth code is found, returns False."""

        # Sets the default settings for the auth code retrieval system.
        authcode_url = 'https://auth.bullhornstaffing.com/oauth/authorize'
        authcode_data = {
            'client_id': self.credentials["client_id"],
            'response_type': 'code',
            'username': self.credentials["username"],
            'password': self.credentials["password"],
            'action': 'Login'}

        # Pulls apart the auth code request to get the aut code itself
        auth_code_request = requests.get(authcode_url, params=authcode_data)
        code = re.search('(?<=code=)[0-9%a-zA-Z-]+', auth_code_request.url)

        # If debugging is enabled then print debug values.
        if self.debug:
            print(authcode_url)
            print(authcode_data)
            print(auth_code_request.url)

        # If no code is found then return Boolean false, otherwise return the authcode.
        if code is None:
            return False

        return unquote(code.group(0))

    def get_token_data(self):
        """Returns the value of the auth token.
        If no token was found, returns false."""

        # By default a cache file does not need to be created.
        need_cache_update = False

        # Checks for the existence of the cache file.
        # If file does not exit then it sets the settings to have one created.
        if os.path.isfile("token_data.json"):
            token_data_file = open("token_data.json", 'r')
            token_cache = json.loads(token_data_file.read())
            token_data_file.close()
            if "error" in token_cache:
                need_cache_update = True
            else:
                need_cache_update = False
                use_refresh_token = True
        else:
            need_cache_update = True
            use_refresh_token = False

        # Set the default values for the token data request.
        token_url = 'https://auth.bullhornstaffing.com/oauth/token'

        # Creates the cache file from scratch
        if need_cache_update:
            token_url_data = {
                'grant_type': 'authorization_code',
                'code': self.get_authcode(),
                'client_id': self.credentials["client_id"],
                'client_secret': self.credentials["client_secret"]}

        # If a refresh token can be used then this sets the settings for that.
        elif use_refresh_token:
            token_url_data = {
                'grant_type': 'refresh_token',
                'refresh_token': token_cache["refresh_token"],
                'client_id': self.credentials["client_id"],
                'client_secret': self.credentials["client_secret"]}

        # If there is no cache file then it creates one with the required data.
        if need_cache_update or use_refresh_token:
            token_request = requests.post(token_url, params=token_url_data)
            token = json.loads(token_request.text)
            token_data_file = open("token_data.json", 'w')
            token["time_expires"] = int(time.time()) + token["expires_in"]
            token_data_file.write(json.dumps(token, indent=3))
            token_data_file.close()

        # Displays useful information for debugging if debugging is enabled.
        if self.debug:
            if need_cache_update or use_refresh_token:
                print(token_url)
                print(token_url_data)
                print(token_request.url)
                print(token_request.text)
                if need_cache_update:
                    print("Created Token Cache from scratch.")
                if use_refresh_token:
                    print("Using refresh token.")

        # Returns the Access Token.
        # If the access token is not present then returns False.
        if "access_token" in token:
            return token["access_token"]

        return False

    def get_rest_access(self):
        """
        Returns the URL and token used to connect to the rest api as a dictionary.
        The 'BhRestToken' index returns the rest API token.
        The 'restUrl' index returns the URL to access the restAPI.
        """

        # Checks for the token_data.json and rest_access.json cache files.
        # If both of the files are present then read them into memory and
        # set the respective variables to reflect the presence of the files.
        # if either of the files are missing or contain errors, update the respective vars.
        if os.path.isfile("token_data.json") and os.path.isfile("rest_access.json"):

            # Read the rest_access.json file into a var
            rest_data_file = open("rest_access.json", 'r')
            rest_cache = json.loads(rest_data_file.read())
            rest_data_file.close()

            # Read the token_data.json file into a var
            token_data_file = open("token_data.json", 'r')
            token_cache = json.loads(token_data_file.read())
            token_data_file.close()

            # If there is an error in the rest cache, set the cache update variable to reflect that
            # a cache rebuild is needed. Otherwise it checks if the cache has expired and if it has
            # it would also mark that the cache needs a rebuild.
            if "error" in token_cache or "error" in rest_cache:
                need_cache_update = True
            else:
                if token_cache["time_expires"] > int(time.time()):
                    need_cache_update = False
                else:
                    need_cache_update = True
        else:
            need_cache_update = True

        # Sets the default settings for rest access authorization.
        if need_cache_update:
            rest_auth_url = 'https://rest.bullhornstaffing.com/rest-services/login'
            rest_auth_data = {
                'version': '*',
                'access_token': self.get_token_data()}
            rest_access_response = requests.get(rest_auth_url, params=rest_auth_data)
            rest_access = json.loads(rest_access_response.text)
            rest_data_file = open("rest_access.json", 'w')
            rest_data_file.write(rest_access_response.text)
            rest_data_file.close()

        # If debugging is enabled then print debug values.
        if self.debug:
            if need_cache_update:
                print(rest_auth_url)
                print(rest_auth_data)
                print(rest_access_response.url)
                print(rest_access)
                print("Created REST Cache from scratch.")

        # Returns the Rest Cache. In dictionary form. Either directly from the request or from the
        # cache file.
        if not need_cache_update:
            return rest_cache

        return rest_access

class DataAccess:
    """Returns the requested data."""

    # init function to be executed when the class is instantiated so that
    # various variables are not missing at method call time.
    def __init__(self, debug=False, meta=False):
        """Sets the required variables for all methods."""

        # Set the initial values for the Data access class.
        self.authenticated_rest = Authentication(debug)
        self.debug = debug
        self.rest_access = self.authenticated_rest.get_rest_access()
        self.meta_flag = meta

    def get_command(self, urlpath, command_options=None):
        """A method that allows for dynamic get commands.
        URL path is the argument that should be executed,
        E.G. restURL/entity/Department?params
        where entity/Department is the urlpath.
        Command_options takes a dictionary"""

        # If there are not arguments passed to the REST get command then
        # it will create the command_ options variable as a blank dictionary.
        if command_options is None:
            command_options = {}

        # Builds the authentication and parameters into the url so that it
        # when it is executed it will be able to log in and perform the requested
        # operations.
        get_command_params = {'BhRestToken': self.rest_access['BhRestToken']}
        get_command_params.update(command_options)

        # Execute the get command on the URL. Grabs the dynamic access URL from the REST Access
        # method's dictionary. Adds the URL path for the get command and then tacks on the
        # parameters/authentication created above.
        result = requests.get(self.rest_access['restUrl'] + urlpath, params=get_command_params)

        # If debugging is enabled then print debug values
        if self.debug:
            print(command_options)
            print(get_command_params)
            print(result.url)

        # Returns the results of the get command in text format.
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

        # Executes a loop that will run as long as the start value, which is incremented by the
        # count value each loop execution, in the returned initial data grab to process at one
        # time does not hit the total value. One each loop the return of the get command is appended
        # to the results dictionary. The loop stops when the start position of the query is higher
        # than the total amount of items that are available.
        while search_params["start"] < loop_end:
            search_params["start"] = search_params["start"] \
            + original_search_request_parsed["count"]
            looped_search_request = json.loads(requests.get(
                self.rest_access['restUrl'] + 'search/' + entity, params=search_params).text)
            results["data"] = results["data"] + looped_search_request["data"]

        # If debugging is enabled then print debug values.
        # If debugging is off then it will minify the printed dictionary.
        if self.debug:
            jsonindent = 3
            print(search_params)
            print(search_request.url)
            print(original_search_request_parsed["count"])
            print(original_search_request_parsed["total"])
        else:
            jsonindent = None

        # Removes the start and count items in the results dictionary to declutter the results.
        results.pop("start")
        results.pop("count")

        # If the metadata flag is enabled then directly return the results.
        # Otherwise, return only the data section.
        if self.meta_flag:
            return json.dumps(results, indent=jsonindent)

        return json.dumps(results["data"], indent=jsonindent)

# Run the program if the program is being executed on the CLI.
# Otherwise suppress execution so that script can act as a library in other projects.
if __name__ == '__main__':
    # Grab the command line arguments.
    COMMAND_LINE_ARGUMENTS = cli_args()
    # Instantiate the Data Access class with the various arguments passed to the program.
    PRINTME = DataAccess(COMMAND_LINE_ARGUMENTS.debug, COMMAND_LINE_ARGUMENTS.meta)
    # Run an API search and print the results to the CLI.
    print(PRINTME.api_search(entity=COMMAND_LINE_ARGUMENTS.entity,
                             fields=COMMAND_LINE_ARGUMENTS.fields))
