#!/usr/bin/env python
from __future__ import with_statement

import logging
import os
import os.path
import sys
import errno
import glob
import filecmp
from shutil import copy2

'''
Name:   Cyrus Raitava-Kumar
UPI:    crai897
'''

# Number of versions by which to keep valid (can be max 9, minimum 1)
validVersions = 6

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn


class VersionFS(LoggingMixIn, Operations):
    def __init__(self):
        # get current working directory as place for versions tree
        self.root = os.path.join(os.getcwd(), '.versiondir')
        # check to see if the versions directory already exists
        if os.path.exists(self.root):
            print('Version directory already exists.')
        else:
            print('Creating version directory.')
            os.mkdir(self.root)

    # Helpers
    # =======

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def isHidden(self, path):
        if (os.path.basename(path)[:1] == "."):
            return True
        return False

    def isTemp(self, path):
        if (os.path.basename(path)[-4:] == ".tmp"):
            return True
        return False

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        # print "access:", path, mode
        full_path = self._full_path(path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        # print "chmod:", path, mode
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        # print "chown:", path, uid, gid
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        # print "getattr:", path
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        # print "readdir:", path
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            for x in os.listdir(full_path):
                if not (self.isHidden(x) | self.isTemp(x)):
                    dirents.append(x)
        for r in dirents:
            yield r

    def readlink(self, path):
        # print "readlink:", path
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        # print "mknod:", path, mode, dev
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        # print "rmdir:", path
        full_path = self._full_path(path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
        # print "mkdir:", path, mode
        return os.mkdir(self._full_path(path), mode)

    def statfs(self, path):
        # print "statfs:", path
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def unlink(self, path):
        # print "unlink:", path
        return os.unlink(self._full_path(path))

    def symlink(self, name, target):
        # print "symlink:", name, target
        return os.symlink(target, self._full_path(name))

    def rename(self, old, new):
        # print "rename:", old, new
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name):
        # print "link:", target, name
        return os.link(self._full_path(name), self._full_path(target))

    def utimens(self, path, times=None):
        # print "utimens:", path, times
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        print('** open:', path, '**')
        full_path = self._full_path(path)

        # Copy file to a temporary file, to compare to upon release
        copy2(full_path, self.hide(full_path) + ".tmp")

        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
        print('** create:', path, '**')
        full_path = self._full_path(path)

        # Check file to be made is NOT hidden
        if not (os.path.basename(full_path)[:1] == "."):

            # Create empty temporary file, to compare to for versioning
            with open(self.hide(full_path) + ".tmp", "w") as f:
                f.write("")

        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
        print('** read:', path, '**')
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        print('** write:', path, '**')
        os.lseek(fh, offset, os.SEEK_SET)

        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        print('** truncate:', path, '**')
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        print('** flush', path, '**')
        return os.fsync(fh)

    # Called ONCE for every open()
    def release(self, path, fh):
        print('** release', path, '**')
        print("\n")

        temp_path = self.hide(self._full_path(path) + '.tmp')

        # Check that a temporary file exists
        if os.path.exists(temp_path):

            # Compare file with specified temp, to see if they are different
            if filecmp.cmp(self._full_path(path), temp_path):

                # Remove temporary file (NOTE POTENTIAL DELAY BETWEEN NEW VERSION CREATION AND TEMP DELETION)
                os.remove(temp_path)
            else :
                self.newversion(self._full_path(path))

                # Remove temporary file (NOTE POTENTIAL DELAY BETWEEN NEW VERSION CREATION AND TEMP DELETION)
                os.remove(temp_path)

        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        print('** fsync:', path, '**')
        return self.flush(path, fh)

    # Method to be called when NEW version is to be made
    def newversion(self, path):

        global validVersions

        # Save basename of input path
        basename = os.path.basename(path)

        # Save dirname of input path
        dirname = os.path.dirname(path)

        # Get list of versions in directory
        versionNames = glob.glob1(dirname, "." + basename + ".[0-9]")
        versionNames.sort()

        # Check how many versions exist, following naming conventions
        numberOfVersions = len(versionNames)

        # Check if we may create another version without having to delete one
        if (numberOfVersions + 1 > validVersions):

            # Shift all filenames over, and make a new file with .1 appended
            for x in reversed(versionNames):

                # Get number of version being dealt with
                versionNumber = int(x[-1:])

                if versionNumber == validVersions:
                    os.remove(self.hide(path) + "." + str(validVersions))
                else:
                    os.rename(self.hide(path) + "." + str(versionNumber), self.hide(path) + "." + str(versionNumber + 1))

            # Copy over contents of newest version, to the newest version
            copy2(path, self.hide(path) + ".1")
        else:

            # Shift all versions
            for x in reversed(versionNames):
                # Get number of version being dealt with
                versionNumber = int(x[-1:])
                os.rename(self.hide(path) + "." + str(versionNumber), self.hide(path) + "." + str(versionNumber + 1))

            # Copy file contents to newest version
            copy2(path, self.hide(path) + ".1")

    # Method to change filename to be hidden if required
    def hide(self, path):
        if os.path.basename(path)[:1] == ".":
            return path
        else :
            return os.path.dirname(path) + "/." + os.path.basename(path)


def main(mountpoint):
    FUSE(VersionFS(), mountpoint, nothreads=True, foreground=True)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1])
