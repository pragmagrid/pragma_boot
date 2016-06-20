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
	#don't need basepath. FIXME rm these lines
	#<param type='string' name='basepath'>
	#The absolute path of pragma_boot [default: /opt/pragma_boot]
	#</param>


	def run(self, params, args):

		(args, vcname) = self.fillPositionalArgs(('vc-name'))

		# Read in site configuration file and imports values:
		#   site_ve_driver, temp_directory,
		#   repository_class, repository_dir, repository_settings
		execfile(self.siteconf, {}, globals())

		# load driver
		driver = pragma.drivers.Driver.factory(site_ve_driver, self.basepath)
		if not driver:
			self.abort("Uknown driver %s" % site_ve_driver)

		if vcname is None:
			clusters = driver.list()
		else:
			clusters = driver.list(vcname)

		if clusters:
			listHeader = "FRONTEND   COMPUTE NODES   STATUS"
			print listHeader 
			for cluster in clusters:
				print "%s" % cluster
	
			return 0
		else:
			return 1

RollName = "pragma_boot"
