class MainArgs:
    """Substitute for argparse.Namespace for tests

    This simply returns None for any undefined attribute which is useful for
    testing the main() functions of subcommands.

    Use this instead of Mock or MagicMock objects for parsed arguments in
    tests.
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        clsname = self.__class__.__name__
        kwargs = [
            f"{attr}={getattr(self, attr)!r}" for attr in dir(self) if not attr.startswith("_")
        ]
        return f"{clsname}({', '.join(kwargs)})"

    def __getattr__(self, attr):
        # Set this on the object so it shows up in repr()
        setattr(self, attr, None)
        return None
