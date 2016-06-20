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
			#print "PRAGMA clusters (%i):" % len(clusters)
			#for cluster in clusters:
			#	print "  %s" % cluster
		else:
			#print "Status of virtual cluster %s" % vcname
			#(frontend, computes, cluster_status) = driver.list(vcname)
			clusters = driver.list(vcname)
			#inactive = []
			#print "  Frontend %s: %s" % (frontend, cluster_status[frontend])
			#if re.search("^active,", cluster_status[frontend]) is None:
			#	inactive.append(frontend)
			#if re.search("up$", cluster_status[frontend]) is None:
			#	inactive.append(frontend)
			#for compute in computes:
			#	print "  Compute %s: %s" % (compute, cluster_status[compute])
			#	if cluster_status[compute] != "active":
			#		inactive.append(compute)
			#if len(inactive) > 0:
			#	sys.exit(1)
			#else:
			#	return 0

		listHeader = "FRONTEND   COMPUTE NODES   STATUS"
		print listHeader 
		for cluster in clusters:
			print "%s" % cluster

		return 0


RollName = "pragma_boot"
