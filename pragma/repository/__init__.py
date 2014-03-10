import xml.etree.ElementTree as ET
import os
import logging
import json
from pragma.repository.processor import process_file

logger = logging.getLogger('pragma_boot')


class BaseRepository(object):
    """
    BaseRepository is an abstract class

    requires "cache_dir" in settings
    """
    # TODO: Think of a better name than "cache_dir"
    def __init__(self, settings={}):
        """
        vcdb is a path to vcdb.json

        vcdb is a dict of vc in this format
        {'vcname': '/path/to/meta.xml', ...}
        """
        super(BaseRepository, self).__init__()
        self.settings = settings
        self.cache_dir = self.settings["cache_dir"]
        self.vcdb_file = None
        self.vcdb = None
        self.vc_file = None
        self.vc = None

    def download_vcdb_file(self):
        raise NotImplementedError

    def get_vcdb_file(self):
        if self.vcdb_file is None:
            self.download_vcdb_file()
        return self.vcdb_file

    def get_vcdb(self):
        with open(self.get_vcdb_file(), 'r') as vcdb_file:
            self.vcdb = json.load(vcdb_file)
        return self.vcdb

    def download_vc_file(self, vcname):
        raise NotImplementedError

    def get_vc_file(self, vcname):
        if self.vc_file is None:
            self.download_vc_file(vcname)
            self.vc_file = os.path.join(self.cache_dir, self.get_vcdb()[vcname])
        return self.vc_file

    def get_vc(self, vcname):
         return ET.parse(self.get_vc_file(vcname))

    def is_downloaded(self):
        raise NotImplementedError

    def download_vc(self, vcname):
        """Download VC to repository cache"""
        raise NotImplementedError

    def delete_vc(self, vcname):
        """Delete VC from repository cache if exists"""
        raise NotImplementedError

    def process_vc(self, vcname):
        base_dir = os.path.dirname(os.path.join(self.cache_dir, self.get_vcdb()[vcname]))
        for f in self.get_vc(vcname).findall("./files/file"):
            process_file(base_dir, f)

    def download_and_process_vc(self, vcname):
        self.download_vc(vcname)
        self.process_vc(vcname)

    def clear_cache(self):
        """Clear repository cache entirely"""
        raise NotImplementedError
