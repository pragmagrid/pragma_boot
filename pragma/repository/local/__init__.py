from pragma.repository import BaseRepository


class Repository(BaseRepository):

    def __init__(self, settings):
        super(Repository, self).__init__(settings)

        self.type = "local"

        self.checkSettings()
        self.checkVcdbFile()


    def checkSettings(self):
        if 'repository_url' in self.settings.keys():
            self.repository_url = self.settings['repository_url']
