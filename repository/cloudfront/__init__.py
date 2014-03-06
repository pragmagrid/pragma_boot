from repository.http import download, Http
from boto.cloudfront.distribution import Distribution
import os


class CloudFront(Http):
    """CloudFront Repository Class"""
    def __init__(self, settings):
        super(CloudFront, self).__init__(settings)
        self.keypair_id = self.settings['keypair_id']
        self.private_key_file = self.settings['private_key_file']
        self.distribution = Distribution()  # Needed to create signed url

    def create_signed_url(self, url):
        """
        Create signed url with no expiration
        """
        return self.distribution.create_signed_url(
            url=url,
            keypair_id=self.keypair_id,
            private_key_file=self.private_key_file
        )

    def get_vcdb(self):
        remote_path = os.path.join(self.baseurl, self.vcdb_filename)
        remote_path = self.create_signed_url(remote_path)
        local_path = os.path.join(self.repodir, self.vcdb_filename)
        download(remote_path, local_path, self.chunk_size)
        return local_path

    def download_vc(self, vcname):
        """
        Download all files specified in vc definition
        """
        for path in self.get_parsed_vc(vcname):
            remote_path = os.path.join(self.baseurl, path)
            remote_path = self.create_signed_url(remote_path)
            local_path = os.path.join(self.repodir, path)
            download(remote_path, local_path, self.chunk_size)
        return True
