from enum import Enum, auto


class UserOrAdminEnum(Enum):
    USER = 0
    ADMIN = 1
    BACK_TO_MAIN_MENU = 2


class UserEnum(Enum):
    SEND_CONFIG = 10


class AdminEnum(Enum):
    SEND_CLIENT_ARGS = 10
    SEND_DESIRED_MESSAGE = 11
    SEND_CLIENT_NUMER_OR_CONFIG = 12

    GET_CLIENT_TELEGRAM_USER = 21

# class UserMenuEnum(Enum):
#     FIRST_MENU = 0
#     SECOND_MENU = 1
