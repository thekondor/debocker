import re
import os
from os.path import join
from codecs import open

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Thanks requests
with open('debocker', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

def files_recursive(path, dest):
    store = []
    for prefix, ds, fs in os.walk(path):
        final_dst = join(dest, prefix)
        store.append((final_dst, [ join(prefix, f) for f in fs ]))
    return store

data_files = files_recursive('bundle-files', '/usr/share/debocker')

setup(
    name = "debocker",
    version = version,
    description = "debocker is a Debian packages builder using docker",
    author = "Tomasz Buchert",
    author_email = "tomasz@debian.org",
    url = "http://anonscm.debian.org/cgit/collab-maint/debocker.git",
    requires = [ 'click (>=3.3)' ],
    install_requires = [ 'click>=3.3' ],
    license = "GPLv3+",
    zip_safe = False,
    scripts = ['debocker'],
    data_files = data_files,
    classifiers = [
        'Environment :: Console',
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: System :: Archiving :: Packaging',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: POSIX :: Linux',
    ],
)
