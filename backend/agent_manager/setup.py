"""
Setup script for the Agent Manager package.
"""
from setuptools import setup, find_packages

setup(
    name="agent_manager",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.95.0",
        "uvicorn>=0.21.1",
        "pydantic>=1.10.7",
        "docker>=6.1.1",
        "kubernetes>=26.1.0",
        "celery>=5.2.7",
    ],
)
