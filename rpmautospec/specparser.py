"""
Parsing RPM macros
"""

import copy
import os
import sys
from tempfile import NamedTemporaryFile

from norpm.macrofile import system_macro_registry
from norpm.specfile import ParserHooks, specfile_expand
from rpmautospec_core import AUTORELEASE_MACRO  # pylint: disable=wrong-import-order

from .compat import rpm

AUTORELEASE_DEFINITION = "E%{?-e*}_S%{?-s*}_P%{?-p:1}%{!?-p:0}_B%{?-b*}"

PYTHON_VERSION = str(sys.version_info[0]) + "." + str(sys.version_info[1])


# pylint: disable=too-few-public-methods


class SpecParserError(Exception):
    """Raised error message when spec parser fails"""


class SpecParser:
    """Abstract class for RPM macro parser"""

    errfd = None

    def query(self, _path, _specfilename):
        """
        Return (epoch, overriden_release) tuple)
        """


class RPMSpecParser(SpecParser):
    """Use RPM to parse spec files"""

    def _query(self, path, specfilename):
        # Note: These calls will alter the results of any subsequent macro expansion
        # when the rpm Python module is used from
        # within this very same Python instance.
        # We call rpm.reloadConfig() immediately after parsing the spec,
        # but it is likely not thread/multiprocess-safe.
        # If another thread/process of this interpreter calls RPM Python bindings
        # in the meantime, they might be surprised a bit,
        # but there's not much we can do.
        rpm.addMacro("_invalid_encoding_terminates_build", "0")
        # rpm.addMacro() doesn’t work for parametrized macros
        rpm.expandMacro(f"%define {AUTORELEASE_MACRO} {AUTORELEASE_DEFINITION}")
        rpm.addMacro("autochangelog", "%nil")
        rpm.addMacro("__python", f"/usr/bin/python{PYTHON_VERSION}")
        rpm.addMacro("python_sitelib", f"/usr/lib/python{PYTHON_VERSION}/site-packages")
        rpm.addMacro("_sourcedir", f"{path}")
        rpm.addMacro("_builddir", f"{path}")
        spec = rpm.spec(specfilename)
        query = "%|epoch?{%{epoch}:}:{}|%{version}\n%{release}\n"
        output = spec.sourceHeader.format(query)
        split_output = output.split("\n")
        return split_output[0], split_output[1]

    def query(self, path, specfilename):
        try:
            with NamedTemporaryFile(mode="w", prefix="rpmautospec-rpmerr-") as errfd:
                try:
                    rpm.setLogFile(errfd)
                    return self._query(path, specfilename)
                except Exception as err:  # pylint: disable=broad-exception-caught
                    with open(errfd.name, "r", errors="replace", encoding="utf-8") as rpmerr_read:
                        raise SpecParserError(rpmerr_read.read()) from err
        finally:
            rpm.setLogFile(sys.stderr)
            rpm.reloadConfig()


class NoRPMHooks(ParserHooks):
    """Gather Epoch/Version/Release definitions through norpm parser"""

    def __init__(self):
        self.tags = {}

    def tag_found(self, name, value, _tag_raw):
        """Gather EclusiveArch, ExcludeArch, BuildArch..."""
        if name in ["epoch", "version", "release"]:
            self.tags[name] = value


class NoRPMSpecParser(SpecParser):
    """Use NoRPM to parse spec files"""

    def __init__(self):
        self.registry = system_macro_registry()
        self.registry.known_norpm_hacks()
        self.registry["dist"] = ""
        name, params = AUTORELEASE_MACRO.split("(")
        params = params.rstrip(")")
        self.registry.define(name, (AUTORELEASE_DEFINITION, params))

    def query(self, _path, specfilename):
        registry = copy.deepcopy(self.registry)
        hooks = NoRPMHooks()
        with open(specfilename, "r", encoding="utf8", errors="ignore") as fd:
            specfile_expand(fd.read(), registry, hooks)
        try:
            release = hooks.tags["release"]
            epoch_version = hooks.tags["version"]
        except KeyError as err:
            raise SpecParserError('"Version:" or "Release:" not set.') from err

        if "epoch" in hooks.tags:
            epoch_version = hooks.tags["epoch"] + ":" + epoch_version
        if "%" in epoch_version:
            raise SpecParserError(f"unexpanded macro in epoch_version: {epoch_version}")
        return epoch_version, release


class AutoSpecParser(SpecParser):
    """Use either RPMSpecParser or NoRPMSpecParser depending on the current
    value in environment variable."""

    def __init__(self):
        self.cache = {}

    def query(self, path, specfilename):
        """
        Return (epoch, overriden_release) tuple)
        """
        parser = os.environ.get("RPMAUTOSPEC_SPEC_PARSER", "rpm")
        if parser not in self.cache:
            self.cache[parser] = RPMSpecParser() if parser == "rpm" else NoRPMSpecParser()
        parser = self.cache[parser]
        return parser.query(path, specfilename)
