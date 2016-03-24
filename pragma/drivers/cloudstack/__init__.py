import logging
import os
import pragma
import pragma.utils
from cloudstack import CloudStackCall

logger = logging.getLogger('pragma.drivers.cloudstack')


class Driver(pragma.drivers.Driver):
	def __init__(self, basepath):
		"""
		Instantiate a new Cloudstack driver to launch virtual cluster

		:return:
		"""
		logger.debug("Loaded driver %s" % self.__class__.__module__)
		driver_conf = os.path.join(basepath, "etc", "cloudstack.conf")
		logger.info("Loading driver information from %s" % driver_conf)

		# loads baseurl, apikey, and secret key values
		execfile(driver_conf, {}, globals())
		self.cloudstackcall = CloudStackCall(baseurl, apikey, secretkey)

		logger.info("Using Cloudstack REST API URL: %s" % baseurl)


		#raise NotImplementedError("Please implement constructor method")


	def allocate(self, cpus, memory, key, enable_ent, vc_in, vc_out, repository):
		"""
		Allocate a new virtual cluster from Cloudstack

		:param cpus: Number of CPUs to instantiate
		:param memory: Amount of memory per compute node
		:param key: Path to SSH Key to install
		:param enable_ent: Boolean to add ENT interfaces to nodes
		:param vc_in: Path to virtual cluster specification
		:param vc_out: Path to new virtual cluster information
		:param repository: Path to virtual cluster repository
		:return:
		"""
		raise NotImplementedError("Please implement allocate method")

	def clean(self, vcname):
		"""
		Unallocate virtual cluster

		:param vcname: Name of virtual cluster to be cleaned
		:return: True if clean was successful, otherwise False
		"""
		raise NotImplementedError("Please implement clean method")

	def deploy(self, vc_in, vc_out, temp_dir):
		"""
		Deploy the specified virtual cluster

		:param vc_in: Virtual cluster source specification
		:param vc_out: Network configuration for new virtual cluster
		:param temp_dir: Path to temporary directory
		:return:
		"""
		print "deploy"
		#raise NotImplementedError("Please implement deploy method")

	def list(self, *argv):
		"""
		Return list of virtual clusters or details about a specific cluster

		:return: List of virtual cluster names or a tuple
			(frontend, computes, cluster_status) where frontend is the
			name of the frontend, computes is an array of compute node names,
			and cluster_status is a hash array where the key is the node
			name and value is a string indicating node status.
		"""
		raise NotImplementedError("Please implement list method")

	def shutdown(self, vcname):
		"""
		Shutdown the nodes of the specified virtual cluster.

		:param vcname: Name of running virtual cluster

		:return: True if cluster is shutdown, otherwise False
		"""
		raise NotImplementedError("Please implement shutdown method")

