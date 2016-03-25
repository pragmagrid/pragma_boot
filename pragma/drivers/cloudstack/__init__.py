import logging
import os
import json
import pragma
import pragma.utils
from cloudstack import CloudStackCall
import urllib2

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
		self.cloudstackcall = CloudStackCall(
			baseurl, apikey, secretkey, templatefilter)

		logger.info("Using Cloudstack REST API URL: %s" % baseurl)

		# prefix for VM names
		self.vmNamePrefix = 'vm-'


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

		vc_out.set_key(key)
		vc_out.set_frontend("vc-1", "10.0.0.1", "vc-1.aist.jp")
		cpus_per_node = {
			"vc-1": 8,
			"vm-vc-1-0": 8,
			"vm-vc-1-1": 8
		}
		vc_out.set_compute_nodes(["vm-vc-1-0", "vm-vc-1-1"], cpus_per_node)
		macs = {
			"vc-1": {"public": "b6:58:ca:00:00:de","private": "b6:58:ca:00:00:de"},
			"vm-vc-1-0": { "private": "b6:58:ca:00:00:d0"},
			"vm-vc-1-1": { "private": "b6:58:ca:00:00:d1"}
		}
		ips = {
			"vm-vc-1-0": "10.0.0.2",
			"vm-vc-1-0": "10.0.0.3"
		}
		vc_out.set_network(macs,ips, "255.255.255.0", "10.1.1.1", "8.8.8.8")
		vc_out.write()

		#(fe_template, compute_template) = self.find_templates(vc_in)
		(fe_template, compute_template) = ("biolinux-frontend-original", "biolinux-compute-original")

		# allocate frontend VM
		try:
			ip, octet = self.cloudstackcall.getFreeIP()
		except TypeError:
			return 0

		if octet is None:
			octet = 1
		name = "%s%d" % (self.vmNamePrefix, octet)
		try:
			res = self.cloudstackcall.allocateVirtualMachine(1, fe_template, name, ip)
		except urllib2.HTTPError as e:
			logging.error("Unable to allocate frontend: %s" % self.cloudstackcall.getError(e))
			return 0
		if ip is None:
			for machine in self.cloudstackcall.listVirtualMachines():
				print machine
		vc_out.set_frontend(name, ip, "vc-1.aist.jp")

		print res

		# allocate compute nodes
		#for i in range(num):
		#	name = "%s%d-compute-%d" % (self.vmNamePrefix, octet, i)
		#	print "name", name
		#	res = self.allocateVirtualMachine(ccpu, computeTmpl, name)
		#	allocation.append(res)


		return 1
		#self.cloudstackcall.allocateVirtualCluster(fe_template,1, compute_template,1,2)


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

	def find_templates(self, vc_in):
		"""
		Deploy the specified virtual cluster

		:param vc_in: Virtual cluster source specification
		:param vc_out: Network configuration for new virtual cluster
		:param temp_dir: Path to temporary directory
		:return:
		"""
		frontend_spec = vc_in.get_disk("frontend")
		frontend_filename = os.path.basename(frontend_spec["file"])
		frontend_templatename = frontend_filename.split(".")[0]
		compute_spec = vc_in.get_disk("compute")
		compute_filename = os.path.basename(compute_spec["file"])
		compute_templatename = compute_filename.split(".")[0]

		frontend_template = None
		compute_template = None
		for template in self.cloudstackcall.listTemplates()["template"]:
			if template["name"] == frontend_templatename:
				frontend_template = template
			if template["name"] == compute_templatename:
				compute_template = template

		if frontend_template == None:
			logger.error("Could not find template %s in Cloudstack" % frontend_templatename)
			return (None, None)
		if compute_template == None:
			logger.error("Could not find template %s in Cloudstack" % compute_templatename)
			return (None, None)
		return (frontend_templatename, compute_templatename)

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

