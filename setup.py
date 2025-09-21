#!/usr/bin/env python3
"""Setup script for Eqiva Smart Radiator Thermostat package."""

from setuptools import setup, find_packages

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

setup(
    name="eqiva-smart-radiator-thermostat",
    version="1.0.3",
    author="Heckie",
    maintainer="Mark Hendriksen",
    description="Python library and CLI for controlling Eqiva Smart Radiator Thermostat via Bluetooth LE",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Heckie75/Eqiva-Smart-Radiator-Thermostat",
    packages=find_packages(include=['eqiva_thermostat', 'eqiva_thermostat.*']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Home Automation",
        "Topic :: System :: Hardware",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "bleak",
        "logManager @ git+https://github.com/hendriksen-mark/logManager.git"
    ],
    entry_points={
        "console_scripts": [
            "eqiva=eqiva_thermostat:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
