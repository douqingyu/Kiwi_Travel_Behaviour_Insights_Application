from app.enums.base_enum import BaseEnum


class Role(BaseEnum):
    """
    Enum class for User Role
    """
    TRAVELLER = "traveller"
    EDITOR = "editor"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPPORT_TECHS = "support_techs"