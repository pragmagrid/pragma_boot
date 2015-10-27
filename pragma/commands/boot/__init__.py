import logging
import pragma.commands
import pragma.utils
import pragma.repository.utils
import os
import xml.etree.ElementTree

class drivers_manager:
    """manages the paths to the various drivers"""

    def set_client_base_path(self, path):
        self.client_driver_base_path = path

    def set_ve_base_path(self, path):
        self.ve_driver_base_path = path

    def allocate(self):
        path = self.ve_driver_base_path + '/allocate'
        return self._get_path(path)

    def pre_fix_driver(self):
        path = self.client_driver_base_path + '/pre_fix_driver'
        return self._get_path(path)

    def fix_images(self):
        path = self.ve_driver_base_path + '/fix_images'
        return self._get_path(path)

    def post_fix_driver(self):
        path = self.client_driver_base_path + '/post_fix_driver'
        return self._get_path(path)

    def pre_boot(self):
        path = self.client_driver_base_path + '/pre_boot'
        return self._get_path(path)

    def boot(self):
        path = self.ve_driver_base_path + '/boot'
        return self._get_path(path)

    def _get_path(self, path):
        #TODO make execution of driver optional
        if os.path.isfile(path):
            return path
        else:
            return None

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
			key, logfile, loglevel) = self.fillParams(
			[('basepath', '/opt/pragma_boot'),
			 ('ipop_serverinfo_url', ""),
			 ('ipop_clientinfo_file', ""),
			 ('key', os.path.expanduser('~/.ssh/id_rsa.pub')),
			 ('logfile', None),
			 ('loglevel', 'ERROR'),
			])

		# Read in site configuration file and imports values:
		#   site_ve_driver, temp_directory,
		#   repository_class, repository_dir, repository_settings
		conf_path = os.path.join(basepath, "etc", "site_conf.conf")
		if not(os.path.exists(conf_path)):
                        self.abort('Unable to find conf file: ' + conf_path)
		execfile(conf_path, {}, globals())

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
		dr_manager = drivers_manager()
		dr_manager.set_ve_base_path( os.path.join(
			basepath, 'pragma', 'drivers', site_ve_driver))

		vc_in_xmlroot = None
		try:
			vc_in_xmlroot = repository.get_vc(vcname)
		except KeyError:
			self.abort('vc-name "' + vcname + '" not found')

		# Download vc to cache
		repository.download_and_process_vc(vcname)
		
		# get the arch
		vc_in_filepath = repository.get_vc_file(vcname)
		if vc_in_xmlroot.findall(
			'./virtualization')[0].attrib['arch'] != "x86_64":
			self.abort("Unsupported arch in " + vc_in_filepath)

		#
		# now we first call fix_image
		#
		# TODO properly set the node_types argument
		(fe_temp_disk_path, comp_temp_disk_path) = self.prepareImage(vc_in_filepath, temp_directory, "frontend,compute", dr_manager, 1)

		#
		# and then we call allocate and create vc-out.xml
		#
		vc_out_filepath = temp_directory + "/vc-out.xml"
		cmdline = [dr_manager.allocate(), str(num_cpus), vc_in_filepath,
				vc_out_filepath, temp_directory, key]
		(stdout, ret) = pragma.utils.getOutputAsList(cmdline)
		if ret != 0:
			self.abort("Error, % cpus unavailable" % num_cpus)
			logger.error(stdout)
			sys.exit(1)
		logger.info("Command: " + ' '.join(cmdline))
		logger.info("Output: " + "\n".join(stdout))
		vc_out_xmlroot = xml.etree.ElementTree.parse(vc_out_filepath)
		pubblic_node = vc_out_xmlroot.findall('./frontend/public')[0]
		public_ip = pubblic_node.attrib["ip"]
		fqdn = pubblic_node.attrib["fqdn"]
		netmask = pubblic_node.attrib["netmask"]
		gw = pubblic_node.attrib["gw"]
		dns_node = vc_out_xmlroot.findall('./network/dns')[0]
		dns_servers = dns_node.attrib["ip"]
		node_names = []
		for node_xml in vc_out_xmlroot.findall('./compute/node'):
			node_names.append(node_xml.attrib["name"])
		# search="local" domain=""
		logger.info("Resource allocated: fqdn=" + fqdn + " - ip=" + public_ip +
		" - netmask=" + netmask + " - gw=" + gw)
		
		#
		# deploy frontend
		#
		self.deployImage(fe_temp_disk_path, fqdn, temp_directory, vc_out_filepath, dr_manager, 1, ipop_serverinfo_url, "0" )
		ipop_serverinfo_url = ipop_serverinfo_url if ipop_serverinfo_url != "" else ipop_clientinfo_file
		if num_cpus > 0 :
			#
			# deploy nodes
			#
			for i in node_names:
				self.deployImage(comp_temp_disk_path, i, temp_directory, vc_out_filepath, dr_manager, 1, ipop_serverinfo_url, "1")

	def prepareImage(self, vc_in_filepath, temp_direcotry, node_type, dr_manager, debug):
		""" prepare virtual images to be run on the current platform """
		# fix_driver
		cmdline = [dr_manager.fix_images(), vc_in_filepath, temp_directory, node_type]
		(stdout, ret) =pragma.utils.getOutputAsList(cmdline)
		filepaths=""
		while( filepaths == "" ):
			filepaths=stdout.pop()
		fe_temp_disk_path = filepaths.split(" ")[0]
		comp_temp_disk_path = filepaths.split(" ")[1]
		return (fe_temp_disk_path, comp_temp_disk_path)
	
	def deployImage(self, temp_disk_path, fqdn, temp_directory, vc_out_filepath, dr_manager, debug, ipop_serverinfo_url, ipop_client ):
	    """ it runs the boot script on a machine once """
	    cmdline = [dr_manager.boot(), temp_disk_path, fqdn, temp_directory, vc_out_filepath, ipop_serverinfo_url, ipop_client ]
	    pragma.utils.getOutputAsList(cmdline)
	
	
RollName = "pragma_boot"

