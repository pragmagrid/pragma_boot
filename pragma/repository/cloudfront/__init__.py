from pragma.repository import BaseRepository
from boto.cloudfront.distribution import Distribution
import os

class CloudFront(BaseRepository):

    def __init__(self, settings):
        super(CloudFront, self).__init__(settings)

        try:
            self.repository_url = self.settings["repository_url"]
        except KeyError:
            self.abort('Check repository_settings{} in configuration file. Missing  \"repository_url\".' )
        try:
            self.keypair_id = self.settings['keypair_id']
        except KeyError:
            self.abort('Check repository_settings{} in configuration file. Missing  \"keypair_id\".' )
        try:
            self.private_key_file = self.settings['private_key_file']
        except KeyError:
            self.abort('Check repository_settings{} in configuration file. Missing  \"private_key_file\".' )

        self.distribution = Distribution()  # Needed to create signed url
        self.checkVcdbFile()

    def getRemoteFielPath(self, fname):
        rpath =  os.path.join(self.repository_url, fname)
        rpath =  self.create_signed_url(rpath)
        return rpath

    def create_signed_url(self, url):
        """ Create signed url with no expiration """
        return self.distribution.create_signed_url(
            url=url,
            keypair_id=self.keypair_id,
            private_key_file=self.private_key_file
        )

