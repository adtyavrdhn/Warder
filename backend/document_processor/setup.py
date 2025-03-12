"""
Setup script for the Document Processor package.
"""
from setuptools import setup, find_packages

setup(
    name="document_processor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.95.0",
        "uvicorn>=0.21.1",
        "pydantic>=1.10.7",
        "langchain>=0.0.200",
        "pypdf>=3.9.0",
        "python-docx>=0.8.11",
        "beautifulsoup4>=4.12.2",
        "html2text>=2020.1.16",
        "sentence-transformers>=2.2.2",
    ],
)
