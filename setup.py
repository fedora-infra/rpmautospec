from pathlib import Path

from setuptools import find_packages, setup


HERE = Path(__file__).parent
with (HERE / "requirements.txt").open("r") as f:
    INSTALL_REQUIRES = [x.strip() for x in f.readlines()]
with (HERE / "test_requirements.txt").open("r") as f:
    TESTS_REQUIRE = [x.strip() for x in f.readlines()]
with (HERE / "rpmautospec" / "version.py").open("r") as f:
    version = {}
    exec(f.read(), version)
    VERSION = version["__version__"]


setup(
    name="rpmautospec",
    version=VERSION,
    description="Package and CLI tool for generating RPM releases and changelogs",
    # Possible options are at https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 3 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Build Tools",
    ],
    license="MIT",
    maintainer="Fedora Infrastructure Team",
    maintainer_email="infrastructure@lists.fedoraproject.org",
    platforms=["Fedora", "GNU/Linux"],
    url="https://pagure.io/Fedora-Infra/rpmautospec",
    keywords="fedora",
    packages=find_packages(include=["rpmautospec", "rpmautospec.*"]),
    include_package_data=True,
    package_data={},
    zip_safe=False,
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    entry_points={"console_scripts": ["rpmautospec = rpmautospec.cli:main"]},
)
