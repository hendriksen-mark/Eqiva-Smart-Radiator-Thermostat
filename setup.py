#!/usr/bin/env python3
"""Setup script for Eqiva Smart Radiator Thermostat package."""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements from requirements.txt
def read_requirements():
    requirements = []
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Handle git dependencies
                    if line.startswith("git+"):
                        requirements.append(line)
                    elif " @ git+" in line:
                        requirements.append(line)
                    else:
                        requirements.append(line)
    return requirements

setup(
    name="eqiva-smart-radiator-thermostat",
    version="1.0.0",
    author="Mark Hendriksen",
    author_email="",
    description="Python library and CLI for controlling Eqiva Smart Radiator Thermostat via Bluetooth LE",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/hendriksen-mark/Eqiva-Smart-Radiator-Thermostat",
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
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "eqiva=eqiva_thermostat:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
