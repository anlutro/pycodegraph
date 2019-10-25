#!/usr/bin/env python

import setuptools


setuptools.setup(
    name="pycodegraph",
    version="0.1",
    license="MIT",
    description="Analyze and make graphs from Python code.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Andreas Lutro",
    author_email="anlutro@gmail.com",
    url="https://github.com/anlutro/pycodegraph",
    packages=setuptools.find_packages(include=("pycodegraph", "pycodegraph.*")),
    install_requires=["allib >= 1.0, < 1.2"],
    entry_points={"console_scripts": ["pycodegraph=pycodegraph.cli:main"]},
)
