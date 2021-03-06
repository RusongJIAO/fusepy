#!/usr/bin/env python
from __future__ import print_function, absolute_import, division

import logging

#cassandra API
import pycassa
#persistent files (metadata) 
import json

from collections import defaultdict
from errno import ENOENT
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

if not hasattr(__builtins__, 'bytes'):
    bytes = str

class Cassandra(LoggingMixIn, Operations):
    'Example memory filesystem. Supports only one level of files.'


    def __init__(self):
        self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        now = time()

        #initialize cassandra

        self.pool = pycassa.pool.ConnectionPool('Keyspace1')
        self.col_fam = pycassa.columnfamily.ColumnFamily(self.pool, 'Standard1')

        try:
        	files_json = self.col_fam.get('files', columns=['metadata'])['metadata']
        	self.files = json.loads(files_json)
        except:
        	#self.files = {}
        	self.files['/'] = dict(st_mode=(S_IFDIR | 0o755), st_ctime=now, st_mtime=now, st_atime=now, st_nlink=2)

    def chmod(self, path, mode):
        self.files[path]['st_mode'] &= 0o770000
        self.files[path]['st_mode'] |= mode
        return 0

    def chown(self, path, uid, gid):
        self.files[path]['st_uid'] = uid
        self.files[path]['st_gid'] = gid

    def create(self, path, mode):
        self.files[path] = dict(st_mode=(S_IFREG | mode), st_nlink=1,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.fd += 1
        return self.fd

    def getattr(self, path, fh=None):
        if path not in self.files:
            raise FuseOSError(ENOENT)

        return self.files[path]

    def getxattr(self, path, name, position=0):
        attrs = self.files[path].get('attrs', {})

        try:
            return attrs[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        attrs = self.files[path].get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        self.files[path] = dict(st_mode=(S_IFDIR | mode), st_nlink=2,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.files['/']['st_nlink'] += 1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        # TODO
        # read from cassandra in an array
        # return (part of) array
		'''
        sizeBlock = 4 # look at read!!
        nbBlock = offset // sizeBlock
        nbNewBlocks = size // sizeBlock + 1

        if(offset%sizeBlock == 0):
        	i = 0
        	result = ""
        	while(i<nbNewBlocks):
        		result = result + self.col_fam.get(path, columns=[str(i+nbBlock)])[str(i+nbBlock)]
        		i= i+1
        	rest = size % sizeBlock 
        	result = result + self.col_fam.get(path, columns = [str(i+nbBlock)])[str(i+nbBlock)][:rest]
        else:
        	result = ""
        	result = result + self.col_fam.get(path, columns = [str(nbBlock)])[str(nbBlock)][(offset%sizeBlock):]
        	i = 1
        	while(i<nbNewBlocks):
        		result = result + self.col_fam.get(path, columns=[str(i+nbBlock)])[str(i+nbBlock)]
        		i=i+1
        	rest = size % sizeBlock 
        	result = result + self.col_fam.get(path, columns = [str(i+nbBlock)])[str(i+nbBlock)][:rest]
		'''
		size = self.files[path]["st_size"]

		sizeBlock = 1*1024*1024 

		nbBlock = offset // sizeBlock
		lenData = size
		rest = sizeBlock - offset % sizeBlock
		if (rest == sizeBlock):
			rest = 0

		nbNewBlocks = (lenData-rest)//sizeBlock
		print("####################")
		print("size = "+str(size))
		print("rest = "+str(rest))
		print("nbNewBlocks"+str(nbNewBlocks))
		print("####################")










		if(rest == 0):
			i = 0
			result2 = ""
			while(i < nbNewBlocks):
				print("********************** i="+ str(i)+"**nbNewBloc="+str(nbNewBlocks)+"***** sum ="+str(i+nbBlock))
				result2 = result2 + self.col_fam.get(path, columns = [str(i+nbBlock)])[str(i+nbBlock)]
				#result2 = result2 + self.col_fam.get(path, columns = ["1"])["1"]
				i = i+1
			if(lenData > nbNewBlocks * sizeBlock):
				result2 = result2 + self.col_fam.get(path, columns = [str(nbNewBlocks+nbBlock)])[str(nbNewBlocks+nbBlock)]
		else:
			tmp = self.col_fam.get(path, columns=[str(nbBlock)])[str(nbBlock)]
			result2 = tmp[-rest:]
			i = 0
			while(i < nbNewBlocks):
				result2 = result2 + self.col_fam.get(path, columns = [str(i+nbBlock+1)])[str(i+nbBlock+1)]
				i = i+1
			if(lenData > rest + nbNewBlocks*sizeBlock):
				result2 = result2 + self.col_fam.get(path, columns = [str(nbNewBlocks+nbBlock+1)])[str(nbNewBlocks+nbBlock+1)]
		                






        #file=self.col_fam.get(path, columns=["content"])
        #self.data[path] = file["content"]
        #return self.data[path][offset:offset + size]
		return result2

    def readdir(self, path, fh):
        return ['.', '..'] + [x[1:] for x in self.files if x != '/']

    def readlink(self, path):
        # TODO
        # read from cassandra in an array
        # return (part of) array
        file=self.col_fam.get(path, columns=["content"])
        self.data[path] = file["content"]
        return self.data[path]

    def removexattr(self, path, name):
        attrs = self.files[path].get('attrs', {})

        try:
            del attrs[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        self.files[new] = self.files.pop(old)

    def rmdir(self, path):
        self.files.pop(path)
        self.files['/']['st_nlink'] -= 1
        

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        attrs = self.files[path].setdefault('attrs', {})
        attrs[name] = value

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        self.files[target] = dict(st_mode=(S_IFLNK | 0o777), st_nlink=1,
                                  st_size=len(source))

        # TODO to update
        self.data[target] = source
        #cassandra
        self.col_fam.insert(target, {"content": self.data[target]})
        self.col_fam.insert("files", {"metadata": json.dumps(self.files)})

    def truncate(self, path, length, fh=None):
        # TODO truncate the file on Cassandra
        self.data[path] = self.data[path][:length]
        self.files[path]['st_size'] = length
        #cassandra
        self.col_fam.insert(path, {"content": self.data[path]})
        self.col_fam.insert("files", {"metadata": json.dumps(self.files)})

    def unlink(self, path):
        self.files.pop(path)
        #update cassandra of file 
        self.col_fam.insert("files", {"metadata": json.dumps(self.files)})
        self.col_fam.remove(path)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        self.files[path]['st_atime'] = atime
        self.files[path]['st_mtime'] = mtime

    def write(self, path, data, offset, fh):
        # TODO write the file on Cassandra
        self.data[path] = self.data[path][:offset] + data
        self.files[path]['st_size'] = len(self.data[path])


        sizeBlock = 1*1024*1024   # 

        #block
        '''

        '''
        '''
        sizeBlock = 4  # 
        nbBlock = offset // sizeBlock
        lenData = len(data)
        rest = (nbBlock+1) * sizeBlock - offset

        nbNewBlocks = (lenData-rest)//sizeBlock

        if(rest == sizeBlock or rest == 0):
        	i = 0
        	while(i < nbNewBlocks):
        		self.col_fam.insert(path, {str(i+nbBlock): data[(i*sizeBlock):((i+1)*sizeBlock)]})
        		i = i+1
        	if(len(data) > i*sizeBlock):
        		self.col_fam.insert(path, {str(i+nbBlock): data[(i*sizeBlock):]})
        else:
        	tmp = self.col_fam.get(path, columns=[str(nbBlock)])[str(nbBlock)]
        	self.col_fam.insert(path, {str(nbBlock): tmp+data[:rest]})
        	i = 0
        	while(i < nbNewBlocks & len(data) >= rest+(i+1)*sizeBlock):
        		self.col_fam.insert(path, {str(i+nbBlock): data[(rest+i*sizeBlock):(rest+ (i+1)*sizeBlock)]})
        		i = i+1
        	if(len(data) >= rest + i*sizeBlock):
        		self.col_fam.insert(path, {str(i+nbBlock): data[(rest+i*sizeBlock):]})
		'''

        nbBlock = offset // sizeBlock
        lenData = len(data)
        rest = sizeBlock - offset % sizeBlock
        if (rest == sizeBlock):
        	rest = 0

        nbNewBlocks = (lenData-rest)//sizeBlock

        if(rest == 0):
        	i = 0
        	while(i < nbNewBlocks):
        		self.col_fam.insert(path, {str(i+nbBlock): data[(i*sizeBlock):((i+1)*sizeBlock)]})
        		i = i+1
        	if(lenData > nbNewBlocks * sizeBlock):
        		self.col_fam.insert(path, {str(nbNewBlocks+nbBlock): data[(nbNewBlocks*sizeBlock):]})
        else:
        	tmp = self.col_fam.get(path, columns=[str(nbBlock)])[str(nbBlock)]
        	self.col_fam.insert(path, {str(nbBlock): tmp+data[:rest]})
        	i = 0
        	while(i < nbNewBlocks):
        		self.col_fam.insert(path, {str(i+nbBlock+1): data[(rest+i*sizeBlock):(rest+ (i+1)*sizeBlock)]})
        		i = i+1
        	if(lenData > rest + nbNewBlocks*sizeBlock):
        		self.col_fam.insert(path, {str(nbNewBlocks+nbBlock+1): data[(rest+nbNewBlocks*sizeBlock):]})
                

        #cassandra
        #self.col_fam.insert(path, {"content": self.data[path]})
        self.col_fam.insert("files", {"metadata": json.dumps(self.files)})
        return len(data)


if __name__ == '__main__':
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)

    logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(Cassandra(), argv[1], foreground=True)
