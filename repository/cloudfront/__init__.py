from repository import BaseRepository


class CloudFront(BaseRepository):
    """CloudFront Repository Class"""
    def __init__(self, settings):
        super(CloudFront, self).__init__(settings)
