from pragma.repository import BaseRepository
import os


VCDB_FILENAME = "vcdb.txt"


class Local(BaseRepository):
    """
    Local Repository Class

    Do nothing!
    """

    def __init__(self, settings):
        super(Local, self).__init__(settings)
        try:
            self.vcdb_filename = self.settings["vcdb_filename"]
        except KeyError:
            self.vcdb_filename = VCDB_FILENAME
        self.vcdb_file = os.path.join(self.cache_dir, self.vcdb_filename)

    def download_vcdb_file(self):
        pass

    def download_vc_file(self, vcname):
        vc_file = self.get_vcdb()[vcname]  # vc_file is a relative path
        local_path = os.path.join(self.cache_dir, vc_file)
        self.vc_file[vcname] = local_path

    def download_vc(self, vcname):
        pass

    def process_vc(self, vcname):
        pass
