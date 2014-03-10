from pragma.repository.processor.baseprocessor import BaseProcessor
from pragma.utils import which
import subprocess


class Gzip(BaseProcessor):
    """
    Gzip Processor

    Decompress a single gzip file
    """
    def __init__(self, base_dir, f):
        """
        Gzip Processor

        Decompress gzip file with pigz or gunzip
        """
        super(Gzip, self).__init__(base_dir, f)

        self.decompressor = which("unpigz")
        if self.decompressor is None:
            self.decompressor = which("gunzip")

    def process(self):
        for part in self.parts:
            subprocess.check_call([self.decompressor, part])
