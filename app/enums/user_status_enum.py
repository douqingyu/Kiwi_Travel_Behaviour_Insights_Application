from enum import Enum

class UserStatus(Enum):
    """
    Enum class for User Status
    """
    ACTIVE = "active"
    BANNED = "banned"

    @classmethod
    def from_value(cls, value):
        for member in cls:
            if member.value == value:
                return member
        raise None