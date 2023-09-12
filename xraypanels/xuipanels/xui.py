from login import Login
from inbounds import Inbounds
from clients import Clients


class XUI(Login, Inbounds, Clients):
    def __init__(self, address: str, https: bool = False, session_cookie: str = None):
        self.address = address
        self.https = https
        self.session_cookie = session_cookie
        self.api_url = f'{self.address}/panel/api/inbounds/'
