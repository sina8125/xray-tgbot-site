from django.conf import settings

from xraypanels.xuipanels.login import Login
from xraypanels.xuipanels.inbounds import Inbounds
from xraypanels.xuipanels.clients import Clients


class XUI(Login, Inbounds, Clients):
    def __init__(self, address: str, username: str, password: str, https: bool = False, session_cookie: str = None):
        self.address = address
        self.https = https
        self.session_cookie = session_cookie
        self.login_time = None
        self.api_url = f'{self.address}/panel/api/inbounds'
        self._username = username
        self._password = password


panel = XUI(
    address=settings.PANEL_ADDRESS,
    username=settings.PANEL_USERNAME,
    password=settings.PANEL_PASSWORD
)
# panel.login()
