import os.path
import syslog
import logging
import pragma.utils


class Driver:
	def __init__(self, basepath):
		self.basepath = basepath
		self.driverconf = None
		self.drivername = None

	def setModuleVals(self):
		""" This funciton is called from the child driver module class
		    It sets values depending on the used child driver class name:
			self.drivername -  for example. "kvm_rocks".
			self.logger - from the module name, example:  pragma.drivers.kvm_rocks
		"""

		self.drivername = self.__module__.split('.')[-1]
		self.checkDriverConf()
		self.logger = logging.getLogger(self.__module__)

	def checkDriverConf(self):
		""" Check if the driver configuration file exists 
		    Exit with error message if not found
		"""
		# sanity check. Return if called outside of the child __init__()
		if not self.drivername:
			return

		if not self.driverconf:
			self.driverconf = os.path.join(self.basepath, "etc", self.drivername + ".conf")
		if not (os.path.exists(self.driverconf)):
			self.abort('Unable to find configuration file: ' + self.driverconf)

	def abort(self, msg):
		syslog.syslog(syslog.LOG_ERR, msg.split('\n')[0])
		raise pragma.utils.CommandError(msg)


	def allocate(self, cpus, memory, key, enable_ent, vc_in, vc_out, repository):
		"""
		Allocate a new virtual cluster from Rocks

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
		Unallocate virtual cluster and clean up disks.

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
		raise NotImplementedError("Please implement deploy method")

	def list(self, *argv):
		"""
		Return list of virtual clusters or details about a specific cluster

		:return: List of virtual cluster names or a tuple
		  (frontend, computes, cluster_status) where frontend is the
		  name of the frontend, computes is an array of compute node names,
		  and cluster_status is a hash array where the key is the node
		  name and value is a string indicating node status.
		"""
		raise NotImplementedError("Please implement clean method")

	def shutdown(self, vcname):
		"""
		Shutdown the nodes of the specified virtual cluster.

		:param vcname: Name of running virtual cluster

		:return: True if cluster is shutdown, otherwise False
		"""
		raise NotImplementedError("Please implement shutdown method")
