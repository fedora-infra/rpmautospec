import copy
import sys
from rpmautospec_core import AUTORELEASE_MACRO

try:
    from norpm.macrofile import system_macro_registry
    from norpm.specfile import specfile_expand, specfile_expand_string
except ImportError:
    pass

from .compat import rpm

AUTORELEASE_DEFINITION = "E%{?-e*}_S%{?-s*}_P%{?-p:1}%{!?-p:0}_B%{?-b*}"

class SpecParser:
    errfd = None
    def query(self, _path, _specfilename, _errfd):
        """
        Return (epoch, overriden_release) tuple)
        """
        return None, None

    def cleanup(self):
        """
        Do necessary cleanups.
        """

    def get_err(self):
        return ""


class RPMSpecParser(SpecParser):
    """ Use RPM to parse spec files """
    def __init__(self):
        super().__init__()
        self._prepare()

    def _prepare(self):
        python_version = str(sys.version_info[0]) + "." + str(sys.version_info[1])

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
        rpm.addMacro("__python", f"/usr/bin/python{python_version}")
        rpm.addMacro(
            "python_sitelib", f"/usr/lib/python{python_version}/site-packages"
        )

    def query(self, path, specfilename, errfd):
        self.errfd = errfd
        rpm.setLogFile(errfd)
        rpm.addMacro("_sourcedir", f"{path}")
        rpm.addMacro("_builddir", f"{path}")
        spec = rpm.spec(specfilename)
        query = "%|epoch?{%{epoch}:}:{}|%{version}\n%{release}\n"
        output = spec.sourceHeader.format(query)
        split_output = output.split("\n")
        return split_output[0], split_output[1]

    def cleanup(self):
        rpm.setLogFile(sys.stderr)
        rpm.reloadConfig()

    def get_err(self):
        with open(self.errfd.name, "r", errors="replace", encoding="utf-8") as rpmerr_read:
            return rpmerr_read.read()


class NoRPMSpecParser(SpecParser):
    """ Use NoRPM to parse spec files """

    def __init__(self):
        self.registry = system_macro_registry()
        self.registry.known_norpm_hacks()
        self.registry["dist"] = ""
        name, params = AUTORELEASE_MACRO.split('(')
        params = params.rstrip(')')
        self.registry.define(name, (AUTORELEASE_DEFINITION, params))

    def query(self, _path, specfilename, _errfd):
        registry = copy.deepcopy(self.registry)
        with open(specfilename, "r", encoding="utf8") as fd:
            specfile_expand(fd.read(), registry)
        epoch_version = specfile_expand_string("%version", registry)
        if "epoch" in registry:
            epoch = specfile_expand_string("%epoch", registry)
            epoch_version = epoch + ":" + epoch_version
        release = specfile_expand_string("%release", registry)
        return epoch_version, release
