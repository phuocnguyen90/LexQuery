from setuptools import setup, find_packages

setup(
    name="shared_libs",
    version="0.1.0",
    description="Shared libraries for LLM providers, utilities, and prompts",
    author="Your Name",
    author_email="your.email@example.com",
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
)
