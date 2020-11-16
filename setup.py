# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in katara_club_api/__init__.py
from katara_club_api import __version__ as version

setup(
	name='katara_club_api',
	version=version,
	description='Custom API',
	author='Jigar Tarpara',
	author_email='team@khatavahi.in',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
