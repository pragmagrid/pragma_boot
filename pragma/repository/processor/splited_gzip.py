from pragma.repository.processor.gzip import Gzip
import os
import subprocess
import logging


logger = logging.getLogger('pragma_boot')


class SplitedGzip(Gzip):
    """docstring for SplitedGzip"""
    def __init__(self, base_dir, f):
        super(SplitedGzip, self).__init__(base_dir, f)
        self.filename = self.f.attrib["filename"]

    def process(self):
        command = "cat %s | %s -f > %s" % (
            " ".join(self.parts),
            self.decompressor,
            os.path.join(self.base_dir, self.filename)
        )
        logger.info("Decompressing splited gzip...")
        logger.debug("Execute: %s" % command)
        subprocess.check_call(command, shell=True)  # DANGER!!

        logger.info("Deleting parts...")
        for part in self.parts:
            os.remove(part)
