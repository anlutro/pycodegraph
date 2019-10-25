#!/usr/bin/env python

import setuptools


setuptools.setup(
    name="pycodegraph",
    packages=setuptools.find_packages(include=("pycodegraph", "pycodegraph.*")),
    version="0.1",
    license="MIT",
    description="Analyze and make graphs from Python code.",
    author="Andreas Lutro",
    author_email="anlutro@gmail.com",
    install_requires=["allib >= 1.0, < 1.2"],
    entry_points={"console_scripts": ["pycodegraph=pycodegraph.cli:main"]},
)
