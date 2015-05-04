#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name = "NVBTally",
    version = "0.0.1",
    packages = find_packages(),

    install_requires = ['requests',
                        'requests_futures',
                        'nvblib',
                        ]
)