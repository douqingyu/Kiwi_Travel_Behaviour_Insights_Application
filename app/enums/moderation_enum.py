from app.enums.base_enum import BaseEnum


class ModerationAction(BaseEnum):
    """
    Enum class for Moderation Action
    """
    EDIT = "edit"
    HIDE = "hide"
    DELETE = "delete"