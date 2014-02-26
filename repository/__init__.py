import os
import shutil
import logging
global logger


logger = logging.getLogger('pragma_boot')


class BaseRepository(object):
    """BaseRepository is an abstract class"""
    # TODO: Think of a better name than "repodir"
    def __init__(self, settings={}):
        """
        vcdb is a path to vcdb.txt

        vc_list is a list of vc in this format
        [(name, path_to_meta_xml), (name, path_to_meta_xml), ... ]
        """
        super(BaseRepository, self).__init__()
        self.settings = settings
        self.repodir = self.settings["repodir"]
        self.vcdb = None
        self.vc_list = None

    def get_repodir(self):
        return self.repodir

    def set_repodir(self, repodir):
        self.repodir = repodir

    def get_vcdb(self):
        return self.vcdb

    def get_vc_list(self):
        if self.vc_list is None:
            self.update_vc_list()
        return self.vc_list

    def update_vc_list(self):
        self.vc_list = list()
        with open(self.get_vcdb, 'r') as vcdb:
            for line in vcdb:
                vc = line.split(',')
                self.vc_list.append(vc)

    def download_vc(self, vc_name):
        """Download VC to repository cache"""
        raise NotImplementedError

    def delete_vc(self, vc_name):
        """Delete VC from repository cache if exists"""
        raise NotImplementedError

    def clear_cache(self):
        """Clear repository cache entirely"""
        for the_file in os.listdir(self.repodir):
            try:
                shutil.rmtree(the_file)
            except Exception as e:
                logger.error(e)
