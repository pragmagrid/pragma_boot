from datetime import datetime
import logging
import pragma.commands
import pragma.conf
import pragma.drivers
import pragma.utils
import os
import tempfile
import xml.etree.ElementTree

class Command(pragma.commands.Command):
	"""
	Boot a virtual cluster using configured VM provisioning tool (see
	examples).

	<arg type='string' name='vc-name'>
	The name of the cluster which should be started.
	</arg>

	<arg type='string' name='num-cpus'>
	The nuber of CPUs requested to start up (default is 0 only frontend will
	be started)
	</arg>

	<param type='string' name='basepath'>
	The absolute path of pragma_boot
	</param>

	<param type='string' name='enable-ipop-client'>
	Start up the IPOP-enabled virtual cluster as an IPOP
	client (to another virtual cluster) using the provided
	IPOP server info file
	</param>

	<param type='string' name='enable-ipop-server'>
	Start up the IPOP-enabled virtual cluster with the
	frontend serving as an IPOP server; once
	initialization is complete, store the IPOP server info
	into the provided URL.  If begins with file://, will
	be stored locally, otherwise will be a REST call if
	begins with http://
	</param>

	<param type='string' name='logfile'>
	Print log commands to file at path instead of stdout.
	</param>

	<param type='string' name='loglevel'>
	Specify level of log messages (default: ERROR)
	</param>

	<param type='string' name='key'>
	The ssh key that will be authorized on the frontend of the cluster 
	(default is /root/.ssh/id_rsa.pub).
	</param>

	<example cmd='boot myPragmaCluster 8'>
        Will create a virtual cluster named myPragmaCluster with one or more
	compute nodes adding up to 8 CPUs.
        </example>
        """

        def run(self, params, args):

		(args, vcname, num_cpus) = self.fillPositionalArgs(
			('vc-name', 'num-cpus'))

		if not vcname:
			self.abort('must supply a name for the virtual cluster')
		if not num_cpus:
			self.abort('must supply the number of CPUs')

                try:
                        num_cpus = int(num_cpus)
                except:
                        self.abort('num-cpus must be an integer')

                #
                # fillParams with the above default values
                #
                (basepath, ipop_clientinfo_file, ipop_serverinfo_url,
			key, logfile, loglevel, memory) = self.fillParams(
			[('basepath', '/opt/pragma_boot'),
			 ('ipop_serverinfo_url', ""),
			 ('ipop_clientinfo_file', ""),
			 ('key', os.path.expanduser('~/.ssh/id_rsa.pub')),
			 ('logfile', None),
			 ('loglevel', 'ERROR'),
			 ('memory', None)
			])

		# Read in site configuration file and imports values:
		#   site_ve_driver, temp_directory,
		#   repository_class, repository_dir, repository_settings
		conf_path = os.path.join(basepath, "etc", "site_conf.conf")
		if not(os.path.exists(conf_path)):
                        self.abort('Unable to find conf file: ' + conf_path)
		execfile(conf_path, {}, globals())

		# create a unique temp dir for storage of files
		#our_temp_dir = tempfile.mkdtemp(
		#	suffix=pragma.utils.get_id(), prefix='pragma-', 
		#	dir=temp_directory)
		our_temp_dir = "/state/partition1/temp/pragma-Kfr02V3292-2015-11-20"

		# Download vcdb
        	repository = pragma.utils.getRepository()
		vc_db_filepath = repository.get_vcdb_file()

		if not os.path.isfile(vc_db_filepath):
			self.abort('vc_db file does not exist at ' +
					vc_db_filepath)
		# create logger
		logging.basicConfig(filename=logfile,
			format='%(asctime)s %(levelname)s %(message)s',
			level=getattr(logging,loglevel.upper()))
		logger = logging.getLogger('pragma_boot')

		# load driver
		driver = pragma.drivers.Driver.factory(site_ve_driver)
		if not  driver:
			self.abort( "Uknown driver %s" % site_ve_driver )

		vc_in_xmlroot = None
		try:
			vc_in_xmlroot = repository.get_vc(vcname)
		except KeyError:
			self.abort('vc-name "' + vcname + '" not found')
		vc_in = pragma.conf.VcIn(vc_in_xmlroot, 
			os.path.dirname(repository.get_vc_file(vcname)))

		# Download vc to cache
		repository.download_and_process_vc(vcname)

		# Check arch
		if vc_in.get_arch() != "x86_64":
			self.abort("Unsupported arch '%s' for %s" % (vc_in.get_arch(), vcname))

		#
		# We call allocate and create vc-out.xml
		#
		vc_out = pragma.conf.VcOut(
			os.path.join(our_temp_dir, "vc-out.xml"))
		driver.allocate( 
			num_cpus, memory, key, vc_in, vc_out, repository)
		driver.prepare_images(vc_in, vc_out, our_temp_dir)
		driver.boot(vc_out)


RollName = "pragma_boot"

