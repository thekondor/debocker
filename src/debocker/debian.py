# debian-related functionality

import os
import re
from shutil import which, copyfile, copytree
from shlex import quote as shell_quote
from os.path import isdir, join, isfile, abspath, splitext, \
    dirname, realpath
from .log import log, fail, LOW
from .utils import log_check_call, log_check_output, \
    tmppath, cached_property, get_filelist, calculate_md5_and_size, \
    cached_constant, CURRENT_TIME
from subprocess import CalledProcessError, DEVNULL
from collections import OrderedDict
from string import Template

class Package:

    def __init__(self, path):
        self.path = path
        self.debian = join(self.path, 'debian')
        self.control = join(self.debian, 'control')
        self.changelog = join(self.debian, 'changelog')
        self.source_format = join(self.debian, 'source', 'format')

    def is_valid(self):
        '''verifies that the current directory is a debian package'''
        return isdir(self.debian) and isfile(self.control) and \
            isfile(self.source_format) and self.format in ['native', 'quilt']

    def assert_is_valid(self):
        if not self.is_valid():
            fail('not in debian package directory')

    @cached_property
    def format(self):
        with open(self.source_format) as f:
            line = f.readline().strip()
        m = re.match(r'^3\.0 \((native|quilt)\)', line)
        if not m:
            fail('unsupported format ({})', line)
        fmt = m.group(1)
        log("Detected format '{}'.".format(fmt), LOW)
        return fmt

    @cached_property
    def native(self):
        return self.format == 'native'

    @cached_property
    def name(self):
        with open(self.control) as f:
            for line in f:
                m = re.match(r'^Source: (\S+)$', line)
                if m:
                    return m.group(1)
        fail('could not find the name of the package')

    @cached_property
    def long_version(self):
        '''long version'''
        with open(self.changelog) as f:
            line = f.readline()
        m = re.match(r'^(\S+) \((\S+)\)', line)
        if not m:
            fail("could not parse package version (from '{}')", line.strip())
        return m.group(2)

    @cached_property
    def version(self):
        '''upstream version'''
        if self.native:
            return self.long_version
        else:
            m = re.match(r'^(.+)-(\d+)$', self.long_version)
            if not m:
                fail('could not parse version ({})', self.long_version)
            return m.group(1)

    @cached_property
    def orig_tarball_candidates(self):
        '''possible original upstream tarballs'''
        formats = [ 'xz', 'gz', 'bz2' ]
        names = [ '{}_{}.orig.tar.{}'.format(self.name, self.version, fmt)
                  for fmt in formats ]
        return names

    @cached_property
    def orig_tarball(self):
        '''finds the original tarball'''
        for name in self.orig_tarball_candidates:
            tarball = join(self.path, '..', name)
            log("Trying tarball candidate '{}'.".format(tarball), LOW)
            if isfile(tarball):
                log("Original tarball found at '{}'.".format(tarball), LOW)
                return tarball
        result = extract_pristine_tar(self.path, self.orig_tarball_candidates)
        if result is not None:
            return result
        fail('could not find original tarball')

    def assert_orig_tarball(self):
        if self.native:
            # for now, we just tar the current directory
            path = tmppath('{}_{}.tar.xz'.format(
                self.name, self.version))
            with open(path, 'wb') as output:
                tar = [ 'tar', 'c', '--xz', '--exclude=.git',
                        '-C', self.path, '.' ]
                log_check_call(tar, stdout = output)
            return path
        else:
            return self.orig_tarball  # simple alias

    def tar_package_debian(self, output, comp = None):
        # TODO: make it reproducible
        compressions = {
            'xz': '--xz'
        }
        tar = [ 'tar', 'c' ]
        if comp:
            tar += [ compressions[comp] ]
        debian = join(self.path, 'debian')
        filelist = get_filelist(debian, self.path)
        tar += [ '--no-recursion', '-C', self.path ]
        tar += filelist
        log_check_call(tar, stdout = output)

    def tar_original_tarball(self, output, stdout):
        orig = self.assert_orig_tarball()
        return orig  # for now

    def build_docker_tarball_to_fd(self, output, buildinfo):
        '''builds the docker tarball that builds the package'''
        controlfile = join(self.path, 'debian', 'control')
        controlfile = abspath(controlfile)
        debianfile = tmppath('debian.tar.xz')
        with open(debianfile, 'wb') as debian:
            self.tar_package_debian(debian, comp = 'xz')
        originalfile = self.assert_orig_tarball()
        originalfile = abspath(originalfile)
        if self.native:
            make_native_bundle(self.name, self.version,
                               controlfile, originalfile,
                               buildinfo, output)
        else:
            make_quilt_bundle(self.name, self.long_version,
                              controlfile, originalfile, debianfile,
                              buildinfo, output)

    def build_docker_tarball(self, filename, buildinfo):
        with open(filename, 'wb') as output:
            self.build_docker_tarball_to_fd(output, buildinfo)


STEPS = OrderedDict([
    ('end', None),
    ('build', 'args_05'),
    ('extract-source', 'args_04'),
    ('install-deps', 'args_03'),
    ('install-utils', 'args_02'),
    ('upgrade', 'args_01')
])

STAGES = STEPS.keys()

class Bundler:

    def __init__(self, name, version, control, dsc_name, buildinfo, native):
        self.name = name
        self.version = version
        self.native = native
        self.control = control
        self.sources = []
        self.dsc_name = dsc_name
        self.step_name = buildinfo['step']
        self.step = STEPS[self.step_name]
        self.image = buildinfo['image']
        self.buildinfo = buildinfo
        self.wdir = tmppath('bundle', directory = True)

    @property
    def format_string(self):
        return ('3.0 (native)' if self.native else '3.0 (quilt)')

    def add_source_file(self, name, path, tag):
        md5, size = calculate_md5_and_size(path)
        self.sources.append({
            'name': name,
            'path': path,
            'md5': md5,
            'size': size,
            'tag': tag
        })

    def write_dsc_file(self):
        '''makes minimal, yet functional .dsc file'''
        path = join(self.wdir, 'source', self.dsc_name)
        with open(path, 'w') as f:
            f.write('Format: {}\n'.format(self.format_string))
            f.write('Source: {}\n'.format(self.name))
            f.write('Version: {}\n'.format(self.version))
            f.write('Files:\n')
            for s in self.sources:
                f.write(' {} {} {}\n'.format(s['md5'], s['size'], s['name']))

    def write_info_file(self, info):
        path = join(self.wdir, 'info')
        with open(path, 'w') as f:
            for k, v in info.items():
                f.write("{}={}\n".format(k, v))

    def write_buildinfo_file(self):
        path = join(self.wdir, 'buildinfo')
        with open(path, 'w') as f:
            f.write("flags='{}'\n".format(self.buildinfo['flags']))

    def write_bundle(self, output):
        '''writes bundle to a given file'''

        os.makedirs(join(self.wdir, 'source'))

        info = OrderedDict()
        info['bundle_version'] = __version__
        info['name'] = self.name
        info['version'] = self.version
        info['format'] = ('native' if self.native else 'quilt')

        def make_link(target, parts):
            return os.symlink(target, join(self.wdir, *parts))

        # control file
        make_link(self.control, [ 'control' ])

        # dsc file
        self.write_dsc_file()
        info['dsc_name'] = self.dsc_name

        # sources
        for s in self.sources:
            name = s['name']
            tag = s['tag']
            make_link(s['path'], [ 'source', name ])
            info[tag] = name

        # info & buildinfo
        self.write_info_file(info)
        self.write_buildinfo_file()

        # bundle files
        bundle_files = find_bundle_files()

        copytree(join(bundle_files, 'steps'),
                 join(self.wdir, 'steps'))
        dockertmpl = join(bundle_files, 'Dockerfile')
        with open(dockertmpl, 'r') as df:
            t = Template(df.read())
            ctx = {
                'image': self.image,
                'args_01': 'none',
                'args_02': 'none',
                'args_03': 'none',
                'args_04': 'none',
                'args_05': 'none'
            }
            if self.step:
                log("Replacing '{}' with '{}'.".format(
                    self.step, CURRENT_TIME))
                if self.step not in ctx:
                    fail('internal error in dockerfile template')
                ctx[self.step] = CURRENT_TIME
            rendered = t.substitute(ctx)
            dockerfile = join(self.wdir, 'Dockerfile')
            with open(dockerfile, 'w') as f:
                f.write(rendered)

        file_list = get_filelist(self.wdir)
        # tar everything
        tar = [ 'tar', 'c', '-h', '--numeric-owner' ]
        tar += [ '--no-recursion' ]
        tar += [ '--owner=0', '--group=0' ]
        tar += [ '--mtime=1970-01-01' ]
        tar += [ '-C', self.wdir ]
        tar += file_list
        log_check_call(tar, stdout = output)

def make_native_bundle(name, version, control,
                       source, buildinfo, output):
    dsc_name = '{}_{}.dsc'.format(name, version)
    bundler = Bundler(name, version, control, dsc_name,
                      buildinfo, native = True)
    _, ext = splitext(source)
    source_name = '{}_{}.tar{}'.format(name, version, ext)
    bundler.add_source_file(source_name, source, 'source_tarball')
    bundler.write_bundle(output = output)

def make_quilt_bundle(name, version, control,
                      original, debian, buildinfo, output):
    dsc_name = '{}_{}.dsc'.format(name, version)
    bundler = Bundler(name, version, control, dsc_name,
                      buildinfo, native = False)
    _, oext = splitext(original)
    _, dext = splitext(debian)
    # TODO: improve
    uversion = version.split('-')[0]
    original_name = '{}_{}.orig.tar{}'.format(name, uversion, oext)
    debian_name = '{}_{}.debian.tar{}'.format(name, version, dext)
    bundler.add_source_file(original_name, original, 'original_tarball')
    bundler.add_source_file(debian_name, debian, 'debian_tarball')
    bundler.write_bundle(output = output)

def extract_pristine_tar(path, candidates):
    # extracts a tarball using pristine-tar
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

def docker_build_bundle(bundle, no_cache, pull):
    '''builds the given image and returns the final image'''
    # TODO: quite ugly, cannot be done cleaner?
    build_log = tmppath()
    bundle_esc = shell_quote(bundle)
    build_log_esc = shell_quote(build_log)
    docker_opts = []
    if no_cache:
        docker_opts.append('--no-cache')
    if pull:
        docker_opts.append('--pull')
    docker_opts = ' '.join(docker_opts)
    log_check_call('docker build {} - < {} | tee {}'.format(
        docker_opts, bundle_esc, build_log_esc), shell = True)
    with open(build_log) as f:
        s = f.read().strip()
        ms = re.findall(r'Successfully built (\S+)', s)
        if len(ms) != 1:
            fail('cannot parse logs (build failed?)')
        image = ms[0]
    return image

@cached_constant
def find_bundle_files():
    '''finds the location of bundle files'''
    debocker_dir = dirname(abspath(realpath(__file__)))
    locations = [ debocker_dir, '/usr/share/debocker' ]
    for loc in locations:
        bundle_files = join(loc, 'bundle-files')
        if isdir(bundle_files):
            log("Bundle files found in '{}'.".format(bundle_files), LOW)
            return bundle_files
    fail('could not find bundle files')
