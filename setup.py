# -*- coding: utf-8 -*-
from setuptools import setup


install_requires = ['requests', 'numpy', 'jellyfish', 'pytz']

setup(
    name='yat_geo_db',
    version='1.1.1',
    author='YAT, LLC',
    author_email='rgoss@yat.ai, jhart@yat.ai',
    packages=['yat_geo_db'],
    license="MIT",
    url='https://github.com/yat-co/yat-geo-db',
    install_requires=install_requires,
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    description='Python SDK for YAT Geo Database',
    long_description=open('README.md').read(),
    zip_safe=True,
)