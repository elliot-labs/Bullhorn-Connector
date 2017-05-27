import re
import json
from urllib.parse import unquote
import requests

# The requests library is available via the PIP installer using:
# "python -m pip install requests"

class Authentication():
    """Provides the authentication strings needed for queries."""
    def __init__(self):
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

    def get_authcode(self):
        """Returns the value of the authentication code."""
        auth_code_request = requests.get(self.authcode_url, params=self.authcode_data)
        code = re.search('(?<=code=)[0-9%a-zA-Z-]+', auth_code_request.url)
        return unquote(code.group(0))

    def get_token_data(self):
        """Returns the value of the token."""
        token_request = requests.post(self.token_url, params=self.token_url_data)
        token = re.search('(?<=\"access_token\" : \")[0-9]{2}:[0-9a-zA-Z-]+', token_request.text)
        return token.group(0)

    def get_rest_access(self):
        """
        Returns the URL and token used to connect ot the rest api as a dictionary.
        The 'BhRestToken' index returns the rest API token.
        The 'restUrl' index returns the URL to access the restAPI.
        """
        rest_access_response = requests.get(self.rest_auth_url, params=self.rest_auth_data)
        rest_access = json.loads(rest_access_response.text)
        return rest_access


class DataAccess:
    """Returns the requested data."""
    def __init__(self):
        self.authenticated_rest = Authentication()
        self.rest_access = self.authenticated_rest.get_rest_access()

    def get_command(self, ):
        """A test method"""
        test_params = {
            'BhRestToken': self.rest_access['BhRestToken'],
            'fields': '*'}
        result = requests.get(self.rest_access['restUrl'] + 'meta/Candidate', params=test_params)
        print(result.url)
        return result.text


if __name__ == '__main__':
    PRINTME = DataAccess()
    print(PRINTME.get_command())
