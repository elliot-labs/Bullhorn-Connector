import re
import json
from urllib.parse import unquote
import requests

# The requests library is available via the PIP installer using:
# "python -m pip install requests"

class Authentication():
    """Provides the authentication strings needed for queries."""
    def __init__(self, debug=False):
        """Sets the default settings for the authentication class"""
        self.authcode_url = 'https://auth.bullhornstaffing.com/oauth/authorize'
        self.authcode_data = {
            'client_id': '***REMOVED***',
            'response_type': 'code',
            'username': '***REMOVED***',
            'password': '***REMOVED***',
            'action': 'Login'}
        self.token_url = 'https://auth.bullhornstaffing.com/oauth/token'
        self.token_url_data = {
            'grant_type': 'authorization_code',
            'code': self.get_authcode(),
            'client_id': self.authcode_data['client_id'],
            'client_secret': '***REMOVED***'}
        self.rest_auth_url = 'https://rest.bullhornstaffing.com/rest-services/login'
        self.rest_auth_data = {
            'version': '*',
            'access_token': self.get_token_data()}
        if debug:
            print(self.authcode_url)
            print(self.authcode_data)
            print(self.token_url)
            print(self.token_url_data)
            print(self.rest_auth_url)
            print(self.rest_auth_data)

    def get_authcode(self, debug=False):
        """Returns the value of the authentication code."""
        auth_code_request = requests.get(self.authcode_url, params=self.authcode_data)
        code = re.search('(?<=code=)[0-9%a-zA-Z-]+', auth_code_request.url)
        if debug:
            print(auth_code_request.url)
        return unquote(code.group(0))

    def get_token_data(self, debug=False):
        """Returns the value of the token."""
        token_request = requests.post(self.token_url, params=self.token_url_data)
        token = re.search('(?<=\"access_token\" : \")[0-9]{2}:[0-9a-zA-Z-]+', token_request.text)
        if debug:
            print(token_request.url)
        return token.group(0)

    def get_rest_access(self, debug=False):
        """
        Returns the URL and token used to connect ot the rest api as a dictionary.
        The 'BhRestToken' index returns the rest API token.
        The 'restUrl' index returns the URL to access the restAPI.
        """
        rest_access_response = requests.get(self.rest_auth_url, params=self.rest_auth_data)
        rest_access = json.loads(rest_access_response.text)
        if debug:
            print(rest_access_response.url)
            print(rest_access)
        return rest_access


class DataAccess:
    """Returns the requested data."""
    def __init__(self):
        self.authenticated_rest = Authentication()
        self.rest_access = self.authenticated_rest.get_rest_access()

    def get_command(self, urlpath, command_options=None, debug=False):
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

        if debug:
            print(command_options)
            print(get_command_params)
            print(result.url)

        return result.text


if __name__ == '__main__':
    PRINTME = DataAccess()
    print(PRINTME.get_command('entity/Department/0'))
    # {'fields': '*'}
