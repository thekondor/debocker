# utilities

from tempfile import TemporaryDirectory
from datetime import datetime
from os.path import join
import os

def cached_constant(f):
    cache = []
    def _f():
        if len(cache) == 0:
            cache.append(f())
        return cache[0]
    return _f

def cached_property(f):
    key = '_cached_' + f.__name__
    def _f(self):
        if not hasattr(self, key):
            setattr(self, key, f(self))
        return getattr(self, key)
    return property(_f)

def Counter(v = 0):
    v = [ v ]
    def _f():
        v[0] += 1
        return v[0]
    return _f

tmpdir = cached_constant(lambda: TemporaryDirectory())
tmpunique = Counter()
CURRENT_TIME = datetime.utcnow().isoformat()

def tmppath(name = None, directory = False):
    '''get a temp. path'''
    count = tmpunique()
    tmp_directory = tmpdir().name
    if name is None:
        name = 'tmp'
    tmp_path = join(tmp_directory, '{:03d}-{}'.format(count, name))
    if directory:
        os.mkdir(tmp_path)
    return tmp_path
