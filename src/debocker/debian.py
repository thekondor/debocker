# debian-related functionality

import os
from shutil import which, copyfile
from .log import log, LOW
from .utils import log_check_call, log_check_output, \
    tmppath, join
from subprocess import CalledProcessError, DEVNULL

def extract_pristine_tar(path, candidates):
    if which('pristine-tar') is None:
        log('No pristine-tar available.', LOW)
        return None
    try:
        tars = log_check_output([ 'pristine-tar', 'list' ], cwd = path)
    except CalledProcessError:
        log('Error in pristine-tar - giving up.', LOW)
        return None
    # let's hope that no non-utf8 files are stored
    thelist = tars.decode('utf-8').split()
    log('Pristine tarballs: {}'.format(thelist), LOW)
    matches = list(set(thelist) & set(candidates))
    if len(matches) > 0:
        m = matches[0]
        log("Found a match: '{}'.".format(m), LOW)
        log_check_call([ 'pristine-tar', 'checkout', m ],
                       cwd = path, stderr = DEVNULL)
        try:
            src = join(path, m)
            dst = tmppath(m)
            copyfile(src, dst)
            log("Tarball extracted to '{}'.".format(dst), LOW)
        finally:
            os.unlink(src)
        return dst
    else:
        log('No matching pristine tar found.', LOW)
        return None
