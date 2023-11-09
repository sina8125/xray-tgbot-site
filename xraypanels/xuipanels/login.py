import requests
from django.utils import timezone

import xraypanels.xuipanels


class Login:

    def login(self: "xraypanels.xuipanels.XUI"):
        login_request = requests.post(url=f'{self.address}/login/',
                                      cookies=None,
                                      data={'username': self._username, 'password': self._password},
                                      verify=self.https)
        if login_request.status_code == 200:
            self.session_cookie = login_request.cookies.get('session')
            if self.session_cookie:
                return True
            else:
                return False
        else:
            return False

    def login_decorator(self: 'xraypanels.xuipanels.XUI', func):
        def inner_login(*args, **kwargs):
            if not self.login_time or timezone.now() - self.login_time > timezone.timedelta(days=10):
                self.login()
                self.login_time = timezone.now()
            return func(*args, **kwargs)

        return inner_login
