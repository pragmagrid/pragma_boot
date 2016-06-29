from pragma.repository import BaseRepository

class Repository(BaseRepository):

    def __init__(self, settings):
        super(Repository, self).__init__(settings)

        self.type = "http"

        self.checkSettings()
        self.checkVcdbFile()


    def checkSettings(self):
        try:
            self.repository_url = self.settings["repository_url"]
        except KeyError:
            self.abort('Check repository_settings{} in configuration file. Missing  \"repository_url\".' )
