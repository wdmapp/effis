import os
import shutil
import subprocess
from .log import CompositionLogger


class Campaign:

    cmd = "hpc_campaign"

    @staticmethod
    def CheckString(value, label):
        if (value is not None) and (not isinstance(value, str)):
            CompositionLogger.RaiserError(
                ValueError,
                "Must give {1} as a string. Supplied {0}".format(value, label)
            )

    def __init__(
        self,
        filename=None,
        hostname=None,
        keyfile=None,
        create=True,
    ):
        if shutil.which(self.cmd) is None:
            CompositionLogger.RaiseError(
                "{0} not found. Cannot use Campaign".format(self.cmd)
            )
        self.CheckString(filename, "filename (path) Campaign initializer")
        self.CheckString(hostname, "hostname")
        self.CheckString(keyfile, "keyfile (path)")
        if (keyfile is not None) and (not os.path.isfile(keyfile)):
            CompositionLogger.RaiseError(
                ValueError,
                "Supplied {0} is not an existing file".format(keyfile)
            )

        self.filename = filename
        self.hostname = hostname
        self.keyfile = keyfile

        if os.path.isfile(self.filename):
            CompositionLogger.Info(
                "Found campaign {0}".format(self.filename)
            )
        elif create:
            CompositionLogger.Info(
                "Creating campaign {0}".format(self.filename)
            )
            self.Create()

    @property
    def _manager_(self):
        cmd = [self.cmd, "manager"]
        for name in ("hostname", "keyfile"):
            attr = getattr(self, name)
            if attr is not None:
                cmd += ["--{0}".format(name), attr]
        return cmd + [self.filename]

    def Manager(
        self,
        cmd,
        *args
    ):
        cmd = self._manager_ + [cmd, *args]
        subprocess.call(cmd)

    def Create(self):
        if not os.path.exists(self.filename):
            self.Manager("create")
        else:
            CompositionLogger.Warning(
                "{0} already exists. Skipping create.".format(self.filename)
            )

    def Dataset(self, filename, name=None):
        self.CheckString(name, "name")
        if not os.path.isfile(self.filename):
            CompositionLogger.Warning(
                "{0} does not exist. Skipping dataset add.".format(
                    self.filename
                )
            )
        elif not os.path.exists(filename):
            CompositionLogger.Warning(
                "{0} does not exist. Skipping dataset add.".format(
                    filename
                )
            )
        elif name is not None:
            self.Manager("dataset", filename, "--name", name)
        else:
            self.Manager("dataset", filename)
