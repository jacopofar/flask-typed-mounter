#!/usr/bin/env python

from distutils.core import setup

setup(name='flask_typed_mounter',
      version='0.2.1',
      description='Decorator to mount a function to a Flask endpoint',
      long_description='''one-line decorator to mount a function to a Flask endpoint which will perform type checking on the call parameters and show the pydoc and a table with the parameters inferred from Python 3.6 type hinting''',
      author='Jacopo Farina',
      author_email='jacopo1.farina@gmail.com',
      license='MIT',
      url='https://github.com/jacopofar/flask-typed-mounter',
      packages=['flask_typed_mounter'],
      classifiers=['Development Status :: 3 - Alpha',
                   'License :: OSI Approved :: MIT License',
                   'Programming Language :: Python :: 3.6'],
      keywords='flask type hinting api mounter',
      install_requires=['flask', 'runtime_typecheck', 'docutils'],
      python_requires='>=3.6'
      )
