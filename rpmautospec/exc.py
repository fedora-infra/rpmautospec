from typing import Optional


class RpmautospecException(Exception):
    """Base class for rpmautospec exceptions."""

    def __init__(self, *args, code: Optional[str] = None, detail: Optional[str] = None):
        super().__init__(*args)
        self.code = code
        self.detail = detail

    def __str__(self):
        if self.detail:
            return f"{', '.join(self.args)}:\n{self.detail}"
        return super().__str__()


class SpecParseFailure(RpmautospecException):
    """Failure parsing spec file."""
