#! /usr/bin/env python

from setuptools import setup

setup(
    name='neuropythy',
    version='0.1.0-SNAPSHOT',
    description='Toolbox for flexible cortical mesh analysis and registration',
    keywords='neuroscience mesh cortex registration',
    author='Noah C. Benson',
    author_email='nben@nyu.edu',
    url='https://github.com/noahbenson/neuropythy/',
    license='GPLv3',
    packages=['neuropythy'],
    install_requires=[
        'numpy>=1.2',
        'scipy>=0.7',
        'nibabel>=1.2',
        'pysistence>=0.4',
        'py4j>=0.9'])