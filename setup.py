#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import os
import sys
pjoin = os.path.join

from setuptools import setup

setup_args = dict(
    name="nbviewer-gitlab",
    version="0.2.0",
    packages=["nbviewer_gitlab"],
    author="The Jupyter Development Team",
    author_email="ipython-dev@scipy.org",
    url="http://nbviewer.ipython.org/gitlab/",
    description="Jupyter Notebook Viewer from GitLab",
    long_description="Custom handlers for GitLab",
    license="BSD",
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
    test_suite="nose.collector",
    setup_requires=[
        "python-gitlab"
    ],
    entry_points={
        "nbviewer.provider.handlers": [
            "gitlab = nbviewer_gitlab:default_handlers"
        ],
        "nbviewer.provider.uri_rewrite": [
            "gitlab = nbviewer_gitlab.url:uri_rewrites"
        ]
    }
)

setup(**setup_args)
