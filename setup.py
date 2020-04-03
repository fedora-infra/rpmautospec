import os.path

from setuptools import setup


HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "requirements.txt"), "r") as f:
    INSTALL_REQUIRES = [x.strip() for x in f.readlines()]
with open(os.path.join(HERE, "test_requirements.txt"), "r") as f:
    TESTS_REQUIRE = [x.strip() for x in f.readlines()]


setup(
    name="rpmautospec",
    version="0.0.8",
    description="Package and CLI tool for generating RPM releases and changelogs",
    # Possible options are at https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Build Tools",
    ],
    license="MIT",
    maintainer="Fedora Infrastructure Team",
    maintainer_email="infrastructure@lists.fedoraproject.org",
    platforms=["Fedora", "GNU/Linux"],
    url="https://pagure.io/Fedora-Infra/rpmautospec",
    keywords="fedora",
    packages=["rpmautospec", "rpmautospec.py2compat"],
    include_package_data=True,
    package_data={},
    zip_safe=False,
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    entry_points={"console_scripts": ["rpmautospec = rpmautospec.cli:main"]},
)
