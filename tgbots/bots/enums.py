from enum import Enum


class UserOrAdminEnum(Enum):
    USER = 0
    ADMIN = 1
    BACK_TO_MAIN_MENU = 2


# class UserMenuEnum(Enum):
#     FIRST_MENU = 0
#     SECOND_MENU = 1


class UserUpdatedConfig(Enum):
    SEND_CONFIG = 0


class UserConfigInfo(Enum):
    SEND_CONFIG = 0


class AdminNewConfig(Enum):
    SEND_CLIENT_ARGS = 0


class AdminSendMessageToUsers(Enum):
    SEND_DESIRED_MESSAGE = 0
