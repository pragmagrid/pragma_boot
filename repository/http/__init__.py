from repository import BaseRepository
import logging
import os
import urllib2
import shutil


logger = logging.getLogger('pragma_boot')
VCDB_FILENAME = "vcdb.json"
CHUNK_SIZE = 16 * 1024


# Helper functions
def download(remote_path, local_path, chunk_size=CHUNK_SIZE):
    """
    Download file from remote_path to local_path

    Return True on success
    """
    logger.info("Downloading %s to %s ..." % (remote_path, local_path))

    # Create directories if neccesary
    local_dir = os.path.dirname(local_path)
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    remote_file = urllib2.urlopen(remote_path)
    with open(local_path, 'wb') as local_file:
        shutil.copyfileobj(remote_file, local_file, chunk_size)
    return True


class Http(BaseRepository):
    """
    Http Repository Class

    Should works with http and https
    Just set "baseurl" in settings
    """
    def __init__(self, settings):
        super(Http, self).__init__(settings)
        self.baseurl = self.settings["baseurl"]
        try:
            self.vcdb_filename = self.settings["vcdb_filename"]
        except KeyError:
            self.vcdb_filename = VCDB_FILENAME
        try:
            self.chunk_size = self.settings["chunk_size"]
        except KeyError:
            self.chunk_size = CHUNK_SIZE

    def get_vcdb(self):
        remote_path = os.path.join(self.baseurl, self.vcdb_filename)
        local_path = os.path.join(self.repodir, self.vcdb_filename)
        download(remote_path, local_path, self.chunk_size)
        return local_path

    def download_vc(self, vcname):
        """
        Download all files specified in vc definition
        """
        for path in self.get_parsed_vc(vcname):
            remote_path = os.path.join(self.baseurl, path)
            local_path = os.path.join(self.repodir, path)
            download(remote_path, local_path, self.chunk_size)
        return True

    def delete_vc(self, vcname):
        for path in self.get_parsed_vc(vcname):
            os.remove(path)
        return True
