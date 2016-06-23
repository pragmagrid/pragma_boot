import os
import pragma.commands
import pragma.drivers


class Command(pragma.commands.Command):
	"""
	Shuts down a virtual cluster but does not unallocate resources.

	<arg type='string' name='vc-name'>
	The name of the cluster which should be shutdown.
	</arg>

	<example cmd='shutdown myPragmaCluster'>
	Will shutdown the virtual cluster named myPragmaCluster.
	</example>
	"""

	def run(self, params, args):

		(args, vcname) = self.fillPositionalArgs(('vc-name'))

		if not vcname:
			self.abort('must supply a name for the virtual cluster')

		# Read in site configuration file and imports values: site_ve_driver
		execfile(self.siteconf, {}, globals())

		# load driver
		driver = self.importDriver(site_ve_driver)
		if not driver:
			self.abort("Uknown driver %s" % site_ve_driver)

		if driver.shutdown(vcname):
			print "\nCluster %s successfully shutdown" % vcname


RollName = "pragma_boot"
