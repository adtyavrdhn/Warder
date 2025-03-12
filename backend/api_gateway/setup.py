"""
Setup script for the API Gateway package.
"""
from setuptools import setup, find_packages

setup(
    name="api_gateway",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.95.0",
        "uvicorn>=0.21.1",
        "pydantic>=1.10.7",
        "python-jose>=3.3.0",
        "passlib>=1.7.4",
        "python-multipart>=0.0.6",
    ],
)
