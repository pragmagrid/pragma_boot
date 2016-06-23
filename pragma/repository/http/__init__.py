from pragma.repository import BaseRepository
import logging
import os
from pragma.utils import which
import subprocess



logger = logging.getLogger('pragma_boot')
VCDB_FILENAME = "vcdb.txt"


class Http(BaseRepository):
    """
    Http Repository Class

    Should works with http and https
    Just set "repository_url" in settings
    """

    @staticmethod
    def download(remote_path, local_path):
        """
        Download file from remote_path to local_path

        Using wget and curl because urllib and urllib2 don't seem to be able
        to complete big file transfers (at least from Google drive)
        """

        wget = which("wget")
        if wget is None:
            curl = which("curl")
            if curl is None:
                raise Exception("Cannot find wget or curl!")

        # Create directories if neccesary
        local_dir = os.path.dirname(local_path)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        logger.info("Downloading %s to %s ..." % (remote_path, local_path))
        if wget != None:
            subprocess.check_call([wget, "-S", "-O", local_path, remote_path])
        else:
            subprocess.check_call([curl, "--retry", "5", "-s", "-L", "-o", local_path, remote_path])

    def __init__(self, settings):
        super(Http, self).__init__(settings)
        self.repository_url = self.settings["repository_url"]
        try:
            self.vcdb_filename = self.settings["vcdb_filename"]
        except KeyError:
            self.vcdb_filename = VCDB_FILENAME

    def download_vcdb_file(self):
        remote_path = os.path.join(self.repository_url, self.vcdb_filename)
        local_path = os.path.join(self.repo, self.vcdb_filename)
        Http.download(remote_path, local_path)
        self.vcdb_file = local_path

    def download_vc_file(self, vcname):
        vc_file = self.get_vcdb()[vcname]  # vc_file is a relative path
        remote_path = os.path.join(self.repository_url, vc_file)
        local_path = os.path.join(self.repo, vc_file)
        Http.download(remote_path, local_path)
        self.vc_file[vcname] = local_path

    def download_vc(self, vcname, vc_in):
        """
        Download all files specified in vc definition
        """
        relative_dir = os.path.dirname(self.get_vcdb()[vcname])

        for filename in self.get_vc(vcname).findall("./files/file/part"):
            remote_path = os.path.join(self.repository_url, relative_dir, filename.text)
            local_path = os.path.join(self.repo, relative_dir, filename.text)
            Http.download(remote_path, local_path)

        for node in vc_in.xml.findall(".//disk/source[@type='network']/../../../.."):
            node_type = node.tag
            filename = "%s_%s.img" % (relative_dir, node_type)
            local_path = os.path.join(self.repo, relative_dir, filename)
            if not(os.path.exists(local_path)):
                host = node.find(".//host").attrib
                source = node.find(".//source").attrib
                remote_path = "%s://%s:%s/%s" % (source["protocol"], host["name"], host["port"], source["name"])
                Http.download(remote_path, local_path)
            new_node = node.find(".//source")
            new_node.tag = "source"
            new_node.attrib = {"file": local_path}


    # TODO: Make delete_vc handle either unprocessed and
    # processed VC
    # def delete_vc(self, vcname):
    #     for path in self.get_parsed_vc(vcname):
    #         os.remove(path)
