#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:et
'''
Usage:
    find_dupes.py [options] [DIR...]

Options:
    -c PATH, --logging-conf PATH  YAML config for logging [default: logging.yaml] 
    -t, --test  show args and exit
    -d, --debug  show debug messages
    -q, --quiet  show fewer messages

'''
from docopt import docopt
import sys
from pprint import pprint
import yaml
import logging
from logging.config import dictConfig
import os.path as osp
import os
import stat
from datetime import datetime
from hashlib import md5
from collections import defaultdict

THIS_DIR = osp.dirname(__file__)

class Digest:
    def __init__(self):
        self.cache = {}

    def __call__(self, path):
        if path not in self.cache:
            self.cache[path] = md5(open(path, 'rb').read()).hexdigest()
        return self.cache[path]

digest = Digest()

class FileInfo(dict):
    def sameDigest(self, other):
        global digest
        return digest(self['path']) == digest(other['path'])

    def __eq__(self, other):
        if self['fsize'] == other['fsize']:
            return self.sameDigest(other)
        return False
    
    def __hash__(self):
        #return hash(tuple((k,v) for k,v in sorted(self.iteritems())))
        return hash(self['fsize'])

class DirWalker(object):
    def __init__(self, root):
        self.root = osp.expanduser(root)
        self.logger = logging.getLogger('DirWalker')

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def __iter__(self):
        global digest
        self.logger.debug('Starting iter: {!r}'.format(self.root))
        start = datetime.now()
        for r,d,files in os.walk(self.root):
            self.logger.debug('r={!r}'.format(r))
            for f in files:
                full = osp.join(r, f)
                s = os.stat(full)
                yield FileInfo(path=full,
                        #mtime=datetime.fromtimestamp(s[stat.ST_MTIME]),
                        mtime=s[stat.ST_MTIME],
                        fsize=s[stat.ST_SIZE],
                        digest=digest(full),
                        )
        elapsed = datetime.now() - start
        logging.info('Scanned {!r} in {}'.format(self.root, elapsed))

if '__main__' == __name__:
    args = docopt(__doc__)
    try:
        dictConfig(yaml.load(open(args['--logging-conf'])))
    except:
        try:
            dictConfig(yaml.load(open(osp.join(THIS_DIR, args['--logging-conf']))))
        except:
            if args['--quiet']:
                level = logging.WARN
            elif args['--debug']:
                level = logging.DEBUG
            else:
                level = logging.INFO
            logging.basicConfig(level=level)
    if args['--test']:
        pprint(args)
        sys.exit(0)
    logging.debug(('args=', args))
    dirs = set(filter(str, args['DIR']))
    if not dirs:
        dirs.add('.')
    logging.info('Scanning dirs: {}'.format(', '.join(map(repr, dirs))))
    count = 0
    files = defaultdict(list)
    for d in dirs:
        with DirWalker(d) as w:
            for f in w:
                count += 1
                logging.debug(('count, f', count, f))
                files[f['digest']].append(f)
    for d, dupes in files.iteritems():
        if len(dupes) > 1:
            print d
            print '\n'.join("  {}".format(x['path']) for x in dupes)

