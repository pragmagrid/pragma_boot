import os
import sys
import subprocess
import logging
from pragma.utils import which

logger = logging.getLogger('pragma_boot')


class FileProcessor:
 
    def __init__(self, base_dir, fname, parts, type="raw"):
        self.base_dir = base_dir # direcotry for virtual images in the repository
        self.filename = fname    # virtyual image filename 

        self.parts = []          # splitted virtual image splitted parts names
        for part in parts:
            self.parts.append(os.path.join(self.base_dir, part))

        # processing functions to call (values)  depending on the file type (keys)
        self.programs = {"gzip": "Gzip",
                         "splited_gzip": "SplitedGzip",
                         "splited": "Splited",
                         "raw": "Raw",
        }

        self.setType(type)
        self.setDecompress()

    def process(self):
        """Call processing function depending on the  file type"""
        prog = self.programs[self.type]
        getattr(self, '%s' % prog)()

    def setType(self,type):
        if type not in self.programs.keys():
            print "Error, don't know program to use for decompressing %s" % type
            sys.exit(-1)

        self.type = type

    def setDecompress(self):
        self.decompressor = None 
        if self.type in ('raw','splitted'):
            return

        self.decompressor = which("gunzip")
        if self.decompressor is None:
            # FIXME add check for not found unpigz
            self.decompressor = which("unpigz")


    def Raw(self):
        """No processing needed"""
        return 


    def Gzip(self):
        """ Decompress a single file """

        for part in self.parts:
            logger.info("Decompressing %s ..." % part)
            logger.debug("Execute: %s %s %s" % (self.decompressor, "-f", part))
            subprocess.check_call([self.decompressor, "-f", part])

    def Splited(self):
        """Combine splitted files into a single image"""

        command = "cat %s > %s" % (" ".join(self.parts),  self.filename)
        logger.debug("Execute: %s" % command)
        subprocess.check_call(command, shell=True)  # DANGER!!

        logger.info("Deleting parts...")
        for part in self.parts:
            os.remove(part)


    def SplitedGzip(self):
        """Combine splitted and decompressed files into a single image"""

        command = "cat %s | %s -f > %s" % ( " ".join(self.parts), self.decompressor, self.filename)
        logger.info("Decompressing splited gzip...")
        logger.debug("Execute: %s" % command)
        subprocess.check_call(command, shell=True)  # DANGER!!

        logger.info("Deleting parts...")
        for part in self.parts:
            os.remove(part)
