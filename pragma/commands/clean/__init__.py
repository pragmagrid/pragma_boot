import os
import pragma.commands
import pragma.drivers
import pragma.utils


class Command(pragma.commands.Command):
	"""
	Unallocates virtual cluster and removes its disk images

	<arg type='string' name='vc-name'>
	The name of the cluster which should be remvoed.
	</arg>

	<example cmd='clean myPragmaCluster'>
	Will remove the virtual cluster named myPragmaCluster.
	</example>
	"""

	def run(self, params, args):

		(args, vcname) = self.fillPositionalArgs(('vc-name'))

		if not vcname:
			self.abort('must supply a name for the virtual cluster')

		# Read in site configuration file and imports values:
		#   site_ve_driver, temp_directory,
		#   repository_class, repository_dir, repository_settings
		execfile(self.siteconf, {}, globals())

		# load driver
		driver = self.importDriver(site_ve_driver)
		if not driver:
			self.abort( "Uknown driver %s" % site_ve_driver )

		print "Removing virtual cluster %s" % vcname
		if driver.clean(vcname):
			print "Cluster %s is successfully removed" % vcname


RollName = "pragma_boot"
