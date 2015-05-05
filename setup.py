#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name = "nvbtally",
    version = "0.0.1",
    packages = find_packages(),

    install_requires = ['requests',
                        'requests_futures',
                        'nvblib>=0.0.1',
                        'pyramid',
                        'pyramid_chameleon',
                        ],

    entry_points="""
    [paste.app_factory]
    main = nvbtally:main
    """,
)