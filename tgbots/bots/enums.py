from enum import Enum


class UserOrAdminEnum(Enum):
    USER = 0
    ADMIN = 1


class UserMenuEnum(Enum):
    FIRST_MENU = 0
    SECOND_MENU = 1


class UserUpdatedConfig(Enum):
    SEND_CONFIG = 0
