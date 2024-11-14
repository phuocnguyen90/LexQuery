from setuptools import setup, find_packages

setup(
    name="shared_libs",
    version="0.1.0",
    description="Shared libraries for LLM providers, utilities, and prompts",
    author="Phuoc Nguyen",
    author_email="phuocnguyen90l@yahoo.com",
    packages=find_packages(),
    install_requires=[
        "requests",
        "boto3",
        "pydantic",
        "PyYAML",
        "redis",
        "python-dotenv"
        # Add other dependencies here as needed
    ],
    package_data={
    'shared_libs.config': ['config.yaml'],  # Include config.yaml in the package data
    },
    include_package_data=True,
)
