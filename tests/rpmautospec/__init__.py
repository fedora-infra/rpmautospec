import contextlib
import os


@contextlib.contextmanager
def temporary_cd(path: str):
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)
