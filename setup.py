from setuptools import setup, find_packages

setup(
    name="aac_processors",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'lxml',
        'deep-translator',
        'langcodes',
    ],
) 