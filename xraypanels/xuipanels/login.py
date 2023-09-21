import requests

import xraypanels.xuipanels


class Login:
    def login(self: "xraypanels.xuipanels.XUI", username: str, password: str):
        if self.session_cookie:
            return True
        login_request = requests.post(url=f'{self.address}/login/',
                                      cookies=None,
                                      data={'username': username, 'password': password},
                                      verify=self.https)
        if login_request.status_code == 200:
            self.session_cookie = login_request.cookies.get('session')
            if self.session_cookie:
                return True
            else:
                return False
        else:
            return False
