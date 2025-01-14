from setuptools import find_packages, setup

setup(
    name="aac-processors",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "lxml>=4.9.3",
        "beautifulsoup4>=4.12.2",
        "pandas>=2.1.1",
        "openpyxl>=3.1.2",
    ],
    entry_points={
        "console_scripts": [
            "aac-processors=aac_processors.cli:main",
        ],
    },
    python_requires=">=3.8",
    description="Process and convert between different AAC file formats",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Will Wade",
    author_email="will@willwade.co.uk",
    url="https://github.com/willwade/AACProcessors",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
