from setuptools import setup
from setuptools.command.build_py import build_py
import pathlib
import shutil


RUNTIME_VENDOR_ITEMS = ("index.html", "lib", "style")


def copy_runtime_vendor(target_root: pathlib.Path) -> None:
    repo_vendor = pathlib.Path(__file__).parent / "vendor" / "somarkdown-viewer"
    package_vendor = target_root / "somark" / "vendor" / "somarkdown-viewer"
    if not repo_vendor.exists():
        return

    if package_vendor.exists():
        shutil.rmtree(package_vendor)
    package_vendor.mkdir(parents=True, exist_ok=True)
    for item in RUNTIME_VENDOR_ITEMS:
        source = repo_vendor / item
        target = package_vendor / item
        if source.is_dir():
            shutil.copytree(source, target)
        elif source.is_file():
            shutil.copy2(source, target)


class BuildPy(build_py):
    def run(self):
        super().run()
        copy_runtime_vendor(pathlib.Path(self.build_lib))


setup(cmdclass={"build_py": BuildPy})
