# utilities

import os
import hashlib
from tempfile import TemporaryDirectory
from datetime import datetime
from os.path import join, relpath
from subprocess import check_call, check_output

from .log import log, LOW

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

def calculate_md5_and_size(path):
    md5 = hashlib.md5()
    count = 0
    with open(path, 'rb') as f:
        while True:
            buff = f.read(8192)
            if len(buff) == 0:
                break
            count += len(buff)
            md5.update(buff)
    return md5.hexdigest(), count

def log_check_call(cmd, **kwds):
    log('Run (check): {}'.format(cmd), LOW)
    return check_call(cmd, **kwds)

def log_check_output(cmd, **kwds):
    log('Run (output): {}'.format(cmd), LOW)
    return check_output(cmd, **kwds)

def get_filelist(path, base = None):
    # reproducible list of files
    if base is None:
        base = path
    elements = []
    for p, ds, fs in os.walk(path):
        p = relpath(p, base)
        if p != '.':
            p = join('.', p)
        elements += [ join(p, x) for x in ds ]
        elements += [ join(p, x) for x in fs ]
    return sorted(elements)
