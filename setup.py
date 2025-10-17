"""
Setup script for dsjconvert package.

This allows the package to be installed via pip and published to PyPI.
"""

from setuptools import setup, find_packages
import os

# Read the README for long description
def read_long_description():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

# Read requirements
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name='dsjconvert',
    version='1.1.0',
    author='dsjconvert contributors',
    author_email='',
    description='Convert SAS datasets to Dataset-JSON v1.1 format',
    long_description=read_long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/cdisc-org/dataset-json',
    project_urls={
        'Documentation': 'https://github.com/cdisc-org/dataset-json',
        'Source': 'https://github.com/cdisc-org/dataset-json',
        'Tracker': 'https://github.com/cdisc-org/dataset-json/issues',
    },
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    package_data={
        'dsjconvert': ['schemas/*.json'],
    },
    include_package_data=True,
    python_requires='>=3.7',
    install_requires=read_requirements(),
    entry_points={
        'console_scripts': [
            'dsjconvert=dsjconvert.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Operating System :: OS Independent',
    ],
    keywords='sas xpt sas7bdat dataset-json cdisc clinical-trials data-exchange',
    license='MIT',
)
