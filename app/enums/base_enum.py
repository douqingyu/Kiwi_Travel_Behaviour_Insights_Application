from enum import Enum

class BaseEnum(Enum):
    """
    Base Enum class with a from_value method
    """
    @classmethod
    def from_value(cls, value):
        for member in cls:
            if member.value == value:
                return member
        raise None