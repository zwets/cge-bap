from setuptools import find_packages, setup

VERSION = '3.0.0'  # sensible default, but get from the bap module
with open("bap/__init__.py", 'r') as f:
    for l in f:
        if l.startswith('__version__'):
             VERSION = l.split('=')[1].strip().strip('"')

NAME = 'bap'
DESCRIPTION = 'CGE Bacterial Analysis Pipeline'
URL = 'https://github.com/zwets/cge-bap'
EMAIL = 'io@zwets.it'
AUTHOR = 'Marco van Zwetselaar'
PLATFORMS = [ 'Linux' ]
REQUIRES_PYTHON = '>=3.9.0'
REQUIRED = ['picoline' ]
EXTRAS = { }

about = {'__version__': VERSION}

setup(
    name = NAME,
    version = VERSION,
    description = DESCRIPTION,
    long_description = DESCRIPTION,
    platforms = PLATFORMS,
    author = AUTHOR,
    author_email = EMAIL,
    python_requires = REQUIRES_PYTHON,
    url = URL,
    packages = find_packages(exclude=["tests"]),
    entry_points={ 'console_scripts': [ 'BAP = bap.BAP:main' ] },
    install_requires = REQUIRED,
    extras_require = EXTRAS,
    include_package_data = True,
    #test_suite="tests",
    license = 'Apache License, Version 2.0',
    classifiers = ['License :: OSI Approved :: Apache Software License'],
    zip_safe = False
    )

