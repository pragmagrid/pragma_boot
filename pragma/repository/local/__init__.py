from pragma.repository import BaseRepository
import os


class Local(BaseRepository):

    def __init__(self, settings):
        super(Local, self).__init__(settings)
        if 'repository_url' in self.settings.keys():
            self.repository_url = self.settings['repository_url']

        self.checkVcdbFile()

