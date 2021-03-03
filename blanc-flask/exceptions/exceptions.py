class AuthenticationException(Exception):
    """Exception with a firebase authentication."""


class InvalidRoomIdException(Exception):
    """Exception for invalid chat room id."""


class NotFoundSuchUserException(Exception):
    """Exception for invalid uid."""
