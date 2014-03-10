from pragma.repository.processor.baseprocessor import BaseProcessor


class Raw(BaseProcessor):
    """
    Raw Processor

    Do nothing
    """
    def __init__(self, base_dir, f):
        super(Raw, self).__init__(base_dir, f)

    def process(self):
        pass
