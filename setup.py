from setuptools import setup, find_packages

setup(
    name='review',
    version='0.1.0',
    packages=find_packages(include=['review', 'review.*'])
)
