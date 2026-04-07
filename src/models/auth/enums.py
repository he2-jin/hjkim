import enum


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"


class DeviceType(str, enum.Enum):
    IOS = "ios"
    ANDROID = "android"
    PC = "pc"
    WEB = "web"
