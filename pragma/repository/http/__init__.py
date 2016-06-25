from pragma.repository import BaseRepository
import logging
import os


class Http(BaseRepository):

    def __init__(self, settings):
        super(Http, self).__init__(settings)
        try:
            self.repository_url = self.settings["repository_url"]
        except KeyError:
            self.abort('Check repository_settings{} in configuration file. Missing  \"repository_url\".' )
        self.checkVcdbFile()

