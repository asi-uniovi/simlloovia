#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['Click>=7.0', 
    'malloovia',
    'simpy',
    'numpy',
    'pandas'
]

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest>=3', ]

setup(
    author="ASI Uniovi",
    author_email='joaquin@uniovi.es',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Simulate transactional systems running on cloud infrastructure",
    entry_points={
        'console_scripts': [
            'simlloovia=simlloovia.cli:simulate',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='simlloovia',
    name='simlloovia',
    packages=find_packages(include=['simlloovia', 'simlloovia.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/asi-uniovi/simlloovia',
    version='1.0.0',
    zip_safe=False,
)
