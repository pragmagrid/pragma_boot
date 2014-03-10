import os


class BaseProcessor(object):
    """BaseProcessor"""
    def __init__(self, base_dir, f):
        super(BaseProcessor, self).__init__()
        self.base_dir = base_dir
        self.f = f  # File

        self.parts = []
        for part in self.f.findall("./part"):
            self.parts.append(os.path.join(self.base_dir, part.text))

    def process(self):
        raise NotImplementedError
