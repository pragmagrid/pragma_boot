# Import processors
from gzip import Gzip
from splited_gzip import SplitedGzip
from splited import Splited
from raw import Raw


DEFAULT_PROCESSOR = "raw"
PROCESSORS = {
    "gzip": Gzip,
    "splited_gzip": SplitedGzip,
    "splited": Splited,
    "raw": Raw,
}


def process_file(base_dir, f):
    """
    Instiate appropriate processor and call process()
    """
    try:
        processor = f.attrib["type"]
    except KeyError:
        processor = DEFAULT_PROCESSOR
    processor = PROCESSORS[processor](base_dir, f)
    processor.process()
