import logging
import os
import pragma.commands


class Command(pragma.commands.Command):
	"""
	Sync local repository to its remote repository

	<param type='string' name='logfile'>
	Print log commands to file at path instead of stdout.
	</param>

	<param type='string' name='loglevel'>
	Specify level of log messages (default: ERROR)
	</param>
	"""

	def makeLog(self, logdir):
		if not os.path.isdir(logdir):
			os.makedirs(logdir)

		return os.path.join(logdir, "sync.log")

	def run(self, params, args):
		# Read in site configuration file and imports values: site_ve_driver
		execfile(self.siteconf, {}, globals())

		# fillParams with the above default values
		(logfile, loglevel) = self.fillParams(
			[('logfile', None), ('loglevel', 'INFO')])

		if logfile is None:
			logfile = self.makeLog(log_directory)
		self.config_logging(loglevel, logfile)
		logger = logging.getLogger(self.__module__)

		logger.info("Syncing remote pragma repository")
		repository = self.getRepository()
		repository.sync()


RollName = "pragma_boot"
