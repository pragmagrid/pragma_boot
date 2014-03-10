from pragma.repository.processor.gzip import Gzip
import os
import subprocess


class SplitedGzip(Gzip):
    """docstring for SplitedGzip"""
    def __init__(self, base_dir, f):
        super(SplitedGzip, self).__init__(base_dir, f)
        self.filename = self.f.attrib["filename"]

    def process(self):
        # NOTE: .gz is required for proper decompression
        output = os.path.join(self.base_dir, "%s.gz" % self.filename)
        with open(output, "w") as out:
            subprocess.check_call((['cat'] + self.parts), stdout=out)
        for part in self.parts:
            os.remove(part)
        subprocess.check_call([self.decompressor, output])
