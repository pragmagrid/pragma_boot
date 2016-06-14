import logging
import os
import pragma
import pragma.utils
from cloudstack import CloudStackCall
import urllib2
import base64
import hashlib

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
		self.vmNamePrefix = 'vc'
		self.nic_names = ["private", "public"]


		#raise NotImplementedError("Please implement constructor method")

	def allocate_machine(self, num_cpus, template, name, ip, ips, macs, cpus_per_node, largest=False):
		try:
			res = self.cloudstackcall.allocateVirtualMachine(num_cpus, template, name, ip, None, largest)
		except urllib2.HTTPError as e:
			logging.error("Unable to allocate frontend: %s" % self.cloudstackcall.getError(e))
			return None
		vm_response = self.cloudstackcall.listVirtualMachines(None, res["id"])
		if "virtualmachine" not in vm_response:
			logger.error("Unable to query for virtual machine %s" % name)
			return None
		nics = vm_response["virtualmachine"][0]["nic"]
		ips[name] = {}
		macs[name] = {}
		for index, nic in enumerate(nics):
			ips[name][self.nic_names[index]] = nics[index]["ipaddress"]
			macs[name][self.nic_names[index]] = nics[index]["macaddress"]
		cpus_used = vm_response["virtualmachine"][0]["cpunumber"]
		cpus_per_node[name] = cpus_used

		return vm_response



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

		#(fe_template, compute_template) = self.find_templates(vc_in)
		(fe_template, compute_template) = ("biolinux-frontend-original", "biolinux-compute-original")

		# allocate frontend VM
		try:
			ip, octet = self.cloudstackcall.getFreeIP()
		except TypeError:
			return 0

		if octet is None:
			octet = 0
		octet += 10 # artificially change IP address to give time to clean others from system; remove from prod code
		name = "%s%d" % (self.vmNamePrefix, octet)
		ips, macs, cpus_per_node = {}, {}, {}
		vm_response = self.allocate_machine(1, fe_template, name, ip, ips, macs, cpus_per_node)
		if vm_response is None:
			logging.error("Unable to create virtual cluster frontend")
			return 0
		macs[name]["public"] = "02:00:7d:4d:00:3d" # remove once 2 nics added
		nic = vm_response["virtualmachine"][0]["nic"][0]
		netmask = nic['netmask']
		gateway = nic['gateway']
		vc_out.set_frontend(name, "10.1.1.1", ips[name]["private"], "%s.aist.jp" % name) # change once 2 nics added

		# allocate compute nodes
		i = 0
		compute_nodes = []
		while(cpus > 0):
			name = "%s%d-compute-%d" % (self.vmNamePrefix, octet, i)
			vm_response = self.allocate_machine(cpus, compute_template, name, None, ips, macs, cpus_per_node, True)
			if vm_response is None:
				logging.error("Unable to create virtual cluster frontend")
				return 0
			compute_nodes.append(name)
			cpus -= cpus_per_node[name]
			logging.info("Allocated VM %s with %i cpus; %i cpus left to allocate" % (name, cpus_per_node[name], cpus))
			i+=1

		vc_out.set_compute_nodes(compute_nodes, cpus_per_node)
		vc_out.set_network(macs,ips, netmask, gateway, "8.8.8.8")
		vc_out.write()

		return 1


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
		frontend = vc_out.get_frontend()
		self.cloudstackcall.updateVirtualMachine(frontend["name"], str(vc_out))
		#for compute in vc_out.get_computes():
		#	compute_vc_out = self.cloud
		#	self.cloudstackcall.updateVirtualMachine(compute, vc_out)




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


	def list(self, vcname=None):
		"""
		Return list of virtual clusters or details about a specific cluster

		:return: An array of virtual machines ordered by cluster 
			each array item has the VM name and its status. 
		"""

        	response = self.cloudstackcall.listVirtualClusters(vcname)
        	return response
			

	def shutdown(self, vcname):
		"""
		Shutdown the nodes of the specified virtual cluster.

		:param vcname: Name of running virtual cluster

		:return: An array of virtual machines ordered by cluster 
		 	 each array item has the VM name and its status. 
		"""
		command = 'stopVirtualCluster'

        	response = self.cloudstackcall.stopVirtualCluster(vcname)
        	return response


