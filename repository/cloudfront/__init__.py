from repository import BaseRepository


class CloudFront(BaseRepository):
    """CloudFront Repository Class"""
    def __init__(self, settings):
        super(CloudFront, self).__init__(settings)

    # TODO: Write me
    def get_vcdb(self):
        pass

    # TODO: Write me
    def download_vc(self, vc_name):
        pass
