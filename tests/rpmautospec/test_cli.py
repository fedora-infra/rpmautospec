import subprocess
import sys


class TestCLI:
    """Test the rpmautospec.cli module"""

    def test_main_help(self):
        """Test that getting top-level help works

        This serves a smoke test around argument parsing. It must execute
        another process because argparse relies on sys.exit() actually stopping
        execution, i.e. mocking it out won't work, because argparse will then
        merrily chug along after displaying help.
        """
        completed = subprocess.run(
            [sys.executable, "-c", "from rpmautospec import cli; cli.main()", "--help"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )

        assert "usage:" in completed.stdout
        assert completed.stderr == ""
