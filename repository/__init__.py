import os
import shutil
import logging
import json


logger = logging.getLogger('pragma_boot')


class BaseRepository(object):
    """
    BaseRepository is an abstract class

    requires "repodir" in settings
    """
    # TODO: Think of a better name than "repodir"
    def __init__(self, settings={}):
        """
        vcdb is a path to vcdb.json

        parsed_vcdb is a list of vc in this format
        {'vcname': '/path/to/meta.xml', ...}
        """
        super(BaseRepository, self).__init__()
        self.settings = settings
        self.repodir = self.settings["repodir"]
        self.vcdb = None
        self.parsed_vcdb = None

    def get_repodir(self):
        return self.repodir

    def set_repodir(self, repodir):
        self.repodir = repodir

    def get_vcdb(self):
        return self.vcdb

    def get_parsed_vcdb(self):
        if self.parsed_vcdb is None:
            self.parse_vcdb()
        return self.parsed_vcdb

    def get_parsed_vc(self, vcname):
        return self.get_parsed_vcdb()[vcname]

    def parse_vcdb(self):
        with open(self.get_vcdb(), 'r') as vcdb:
            self.parsed_vcdb = json.load(vcdb)
        return True

    def download_vc(self, vcname):
        """Download VC to repository cache"""
        raise NotImplementedError

    def delete_vc(self, vcname):
        """Delete VC from repository cache if exists"""
        raise NotImplementedError

    def clear_cache(self):
        """Clear repository cache entirely"""
        for the_file in os.listdir(self.repodir):
            try:
                shutil.rmtree(the_file)
            except Exception as e:
                logger.error(e)
        return True
