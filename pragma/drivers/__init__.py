import logging

logger = logging.getLogger('pragma.drivers')

class Driver:
	def __init__(self):
		raise Exception("Unable to create an instance of abstract class %s" % self)

	@staticmethod
	def factory(driver_name):
		"""
		Create an instance of driver 

		:param driver_name: Name of pragma driver
		:return: An instance of pragma driver
		"""
		driver_class = 'pragma.drivers.%s.Driver' % driver_name
		logger.info( "Loading driver %s" % driver_class )
		fullpath = driver_class.split(".")
		from_module = ".".join(fullpath[:-1])
		classname = fullpath[-1]
		module = __import__(from_module, fromlist=[classname])
		klass = getattr(module, classname)
		return klass()

	def allocate(self, cpus, memory, key, vc_in, vc_out, repository):
		"""
		Allocate a new virtual cluster from Rocks

		:param cpus: Number of CPUs to instantiate
		:param memory: Amount of memory per compute node
		:param key: Path to SSH Key to install
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
