#!/usr/bin/env python
# encoding=utf-8

import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='datofeil',
      version='0.1dev',
      description='Fikser datofeil på nowp',
      keywords='wikipedia bot',
      author='Dan Michael Heggø',
      author_email='danmichaelo@gmail.com',
      url='https://github.com/danmichaelo/datofeil',
      license='MIT',
      packages=['datofeil'],
      install_requires=['mwclient', 'mwtemplates', 'psutil']
      )
