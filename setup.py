#!/usr/bin/env python
# encoding=utf-8

import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='cs1cleanup',
      version='0.1dev',
      description='Fixes CS1 errors on no.wikipedia',
      keywords='wikipedia bot',
      author='Dan Michael Heggø',
      author_email='danmichaelo@gmail.com',
      url='https://github.com/danmichaelo/wikipedia-cs1cleanup',
      license='MIT',
      packages=['cs1cleanup'],
      install_requires=['mwclient', 'mwtemplates', 'psutil', 'six']
      )
