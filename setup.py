from setuptools import setup, find_packages

setup(
    name="arbig",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "vnpy==4.0.0",
        "vnpy-ctp>=6.7.7.1",
        "pandas>=1.3.0",
        "numpy>=1.21.0",
        "pymongo>=4.0.0",
        "redis>=4.0.0",
        "pytz>=2021.1",
        "python-dotenv>=0.19.0",
        "loguru>=0.5.3",
        "pytest>=6.2.5",
        "pytest-cov>=2.12.0",
    ],
) 