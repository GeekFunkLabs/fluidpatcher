import pathlib
import platform
import subprocess
import sysconfig

from setuptools import setup
from setuptools.command.build_py import build_py


class build_py_with_patchcord(build_py):
    def run(self):
        super().run()
        self.build_patchcord()

    def build_patchcord(self):
        system = platform.system().lower()
        if system != "linux":
            print("Skipping patchcord build (non-Linux platform)")
            return

        src = pathlib.Path("src/fluidpatcher/_ladspa/patchcord.c")

        if not src.exists():
            print("patchcord source missing, skipping build")
            return

        target = pathlib.Path(self.build_lib) / "fluidpatcher/_ladspa/patchcord.so"
        target.parent.mkdir(parents=True, exist_ok=True)

        cc = sysconfig.get_config_var("CC") or "cc"
        cflags = sysconfig.get_config_var("CFLAGS") or ""

        cmd = [
            cc,
            "-shared",
            "-fPIC",
            *cflags.split(),
            str(src),
            "-o",
            str(target),
        ]

        try:
            print("Compiling patchcord LADSPA plugin...")
            subprocess.check_call(cmd)
            print("patchcord build complete")
        except Exception as e:
            print("patchcord build failed:", e)
            print("Continuing without patchcord support")


setup(
    cmdclass={
        "build_py": build_py_with_patchcord,
    },
)

