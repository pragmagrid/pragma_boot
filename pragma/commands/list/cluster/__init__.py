import os
import pragma.commands
import pragma.drivers
import pragma.utils
import re
import sys

class Command(pragma.commands.Command):
	"""
	List the clusters and cluster status

	<arg type='string' name='vc-name'>
	The name of the cluster to retrieve status for.
	</arg>

	<example cmd='list cluster'>
	List pragma clusters.
	</example>

	<example cmd='list cluster myPragmaCluster'>
	Show the staus of specified cluster.
	</example>
	"""

	def run(self, params, args):

		(args, vcname) = self.fillPositionalArgs(('vc-name'))

		# Read in site configuration file and imports values: site_ve_driver
		execfile(self.siteconf, {}, globals())

		# load driver
		driver = self.importDriver(site_ve_driver)
		if not driver:
			self.abort("Uknown driver %s" % site_ve_driver)

		if vcname is None:
			clusters = driver.list()
		else:
			clusters = driver.list(vcname)

		if clusters:
			for cluster in clusters:
				print "%s" % cluster
	
			return 0
		else:
			return 1

RollName = "pragma_boot"
