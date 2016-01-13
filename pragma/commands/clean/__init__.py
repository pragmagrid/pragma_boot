import logging
import os
import pragma.commands
import pragma.drivers
import pragma.utils
import re
import sys
import time

class Command(pragma.commands.Command):
	"""
	Unallocates virtual cluster and cleans out images

	<arg type='string' name='vc-name'>
	The name of the cluster which should be cleaned.
	</arg>

	<example cmd='clean myPragmaCluster'>
        Will clean out the virtual cluster named myPragmaCluster.
        </example>
        """

        def run(self, params, args):

		(args, vcname) = self.fillPositionalArgs(('vc-name'))

		if not vcname:
			self.abort('must supply a name for the virtual cluster')

		#
		# fillParams with the above default values
		#
		[basepath] = self.fillParams([('basepath', '/opt/pragma_boot')])

		# Read in site configuration file and imports values:
		#   site_ve_driver, temp_directory,
		#   repository_class, repository_dir, repository_settings
		conf_path = os.path.join(basepath, "etc", "site_conf.conf")
		if not(os.path.exists(conf_path)):
			self.abort('Unable to find conf file: ' + conf_path)
		execfile(conf_path, {}, globals())

		# load driver
		driver = pragma.drivers.Driver.factory(site_ve_driver)
		if not driver:
			self.abort( "Uknown driver %s" % site_ve_driver )

		print "Cleaning virtual cluster %s" % vcname
		if driver.clean(vcname):
			print "Cluster %s successfully cleaned" % vcname
 

RollName = "pragma_boot"

