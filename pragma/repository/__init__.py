import xml.etree.ElementTree as ET
import os
import syslog
import logging
import pragma.utils
from pragma.repository.processor import process_file


class BaseRepository(object):
    def __init__(self, settings={}):
        """
        vcdb is a path to vcdb.json

        vcdb is a dict of vc in this format
        {'vcname': '/path/to/meta.xml', ...}
        """
        super(BaseRepository, self).__init__()
        self.settings = settings
        try:
            self.repo = self.settings["repository_dir"]
        except KeyError:
            self.abort('Check repository_settings{} in configuration file. Missing  \"repository_dir\".' )

        self.vcdb_file = None
        self.vcdb = {}
        self.vc_file = {}

	logging.basicConfig()
	self.logger = logging.getLogger('pragma.repository')

    def abort(self, msg):
        syslog.syslog(syslog.LOG_ERR, msg)
        raise pragma.utils.CommandError(msg)

    def listRepository(self):
        print "DEBUG: in listRepository", self.__module__

    def download_vcdb_file(self):
        raise NotImplementedError

    def get_vcdb_file(self):
        if self.vcdb_file is None:
            self.download_vcdb_file()
        self.checkVcdbFile()
        return self.vcdb_file

    def checkVcdbFile (self):
        """ check if the file exists """
        if not os.path.isfile(self.vcdb_file):
            self.abort ('File %s does not exist.' % self.vcdb_file)

    def get_vcdb(self):
        with open(self.get_vcdb_file(), 'r') as vcdb_file:
            for line in vcdb_file:
                vcname, vc_file = line.strip().split(',')
                self.vcdb[vcname] = vc_file
        return self.vcdb

    def download_vc_file(self, vcname):
        raise NotImplementedError

    def get_vc_file(self, vcname):
        if vcname not in self.vc_file:
            self.download_vc_file(vcname)
        return self.vc_file[vcname]

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
        base_dir = os.path.dirname(os.path.join(self.repo, self.get_vcdb()[vcname]))
        for f in self.get_vc(vcname).findall("./files/file"):
            process_file(base_dir, f)

    def download_and_process_vc(self, vcname, vc_in):
        self.download_vc(vcname, vc_in)
        self.process_vc(vcname)

    def clear_cache(self):
        """Clear repository cache entirely"""
        raise NotImplementedError
