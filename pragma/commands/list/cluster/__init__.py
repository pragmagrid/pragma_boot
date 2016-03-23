import os
import pragma.commands
import pragma.drivers
import re
import sys


class Command(pragma.commands.Command):
	"""
	List the clusters and cluster status

	<param type='string' name='basepath'>
	The absolute path of pragma_boot [default: /opt/pragma_boot]
	</param>

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

		#
		# fillParams with the above default values
		#
		[basepath] = self.fillParams([('basepath', '/opt/pragma_boot')])

		# Read in site configuration file and imports values:
		#   site_ve_driver, temp_directory,
		#   repository_class, repository_dir, repository_settings
		conf_path = os.path.join(basepath, "etc", "site_conf.conf")
		if not (os.path.exists(conf_path)):
			self.abort('Unable to find conf file: ' + conf_path)
		execfile(conf_path, {}, globals())

		# load driver
		driver = pragma.drivers.Driver.factory(site_ve_driver)
		if not driver:
			self.abort("Uknown driver %s" % site_ve_driver)

		if vcname is None:
			clusters = driver.list()
			print "PRAGMA clusters (%i):" % len(clusters)
			for cluster in clusters:
				print "  %s" % cluster
		else:
			print "Status of virtual cluster %s" % vcname
			(frontend, computes, cluster_status) = driver.list(vcname)
			inactive = []
			print "  Frontend %s: %s" % (frontend, cluster_status[frontend])
			if re.search("^active,", cluster_status[frontend]) is None:
				inactive.append(frontend)
			if re.search("up$", cluster_status[frontend]) is None:
				inactive.append(frontend)
			for compute in computes:
				print "  Compute %s: %s" % (compute, cluster_status[compute])
				if cluster_status[compute] != "active":
					inactive.append(compute)
			if len(inactive) > 0:
				sys.exit(1)
			else:
				return 0


RollName = "pragma_boot"
