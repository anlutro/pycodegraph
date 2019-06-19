#!/usr/bin/env python

from setuptools import setup


setup(
    name="pycodegraph",
    packages=["pycodegraph"],
    version="0.0.0",
    license="MIT",
    description="Graph Python code.",
    author="Andreas Lutro",
    author_email="anlutro@gmail.com",
    install_requires=["allib >= 1.0, < 1.2"],
    entry_points={
        "console_scripts": [
            "pycodegraph=pycodegraph.cli:main",
            "pcg-imports=pycodegraph.cli:ImportsEntrypoint.main",
        ]
    },
)
