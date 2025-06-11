#!/usr/bin/env python3
"""
Setup script for Telegram Channel Copy Bot
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="telegram-channel-copy-bot",
    version="2.0.0",
    author="TelegramBot Team",
    author_email="admin@example.com",
    description="A modular Telegram bot for copying messages between channels",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/TelegrambotCopy",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Chat",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "telegram-copy-bot=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.env.example"],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/TelegrambotCopy/issues",
        "Source": "https://github.com/yourusername/TelegrambotCopy",
        "Documentation": "https://github.com/yourusername/TelegrambotCopy/blob/main/README.md",
    },
) 