from pragma.repository.http import Http
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

    def download_vcdb_file(self):
        remote_path = os.path.join(self.repository_url, self.vcdb_filename)
        remote_path = self.create_signed_url(remote_path)
        local_path = os.path.join(self.cache_dir, self.vcdb_filename)
        CloudFront.download(remote_path, local_path, self.chunk_size)
        self.vcdb_file = local_path

    def download_vc_file(self, vcname):
        vc_file = self.get_vcdb()[vcname]  # vc_file is a relative path
        remote_path = os.path.join(self.repository_url, vc_file)
        remote_path = self.create_signed_url(remote_path)
        local_path = os.path.join(self.cache_dir, vc_file)
        CloudFront.download(remote_path, local_path, self.chunk_size)
        self.vc_file = local_path

    def download_vc(self, vcname):
        """
        Download all files specified in vc definition
        """
        relative_dir = os.path.dirname(self.get_vcdb()[vcname])
        for filename in self.get_vc(vcname).findall("./files/file/part"):
            remote_path = os.path.join(self.repository_url, relative_dir, filename.text)
            remote_path = self.create_signed_url(remote_path)
            local_path = os.path.join(self.cache_dir, relative_dir, filename.text)
            CloudFront.download(remote_path, local_path, self.chunk_size)
