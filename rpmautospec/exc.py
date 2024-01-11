class RpmautospecException(Exception):
    """Base class for rpmautospec exceptions."""


class SpecParseFailure(RpmautospecException):
    """Failure parsing spec file."""
