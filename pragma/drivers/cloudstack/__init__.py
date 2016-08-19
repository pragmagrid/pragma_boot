import os
import urllib2
import base64
import hashlib
import logging
import pragma
import pragma.utils
from cloudstack import CloudStackCall


class Driver(pragma.drivers.Driver):
	def __init__(self, basepath):
		pragma.drivers.Driver.__init__(self, basepath)
		self.setModuleVals()

		# loads baseurl, apikey, and secret key values
		execfile(self.driverconf, {}, globals())

		# create instance of CloudStack API
		self.cloudstackcall = CloudStackCall( baseurl, apikey, secretkey, templatefilter)

		# prefix for VM names
		self.vmNamePrefix = 'vc'
		self.nic_names = ["private", "public"]

		self.logger.info("Using Cloudstack REST API URL: %s" % baseurl)
		self.logger.info("Loading driver %s information from %s" % (self.drivername, self.driverconf) )


	def allocate(self, cpus, memory, key, enable_ent, repository):
		"""
		Allocate a new virtual cluster from Cloudstack

		:param cpus: Number of CPUs to instantiate
		:param memory: Amount of memory per compute node
		:param key: Path to SSH Key to install
		:param enable_ent: Boolean to add ENT interfaces to nodes
		:param repository: repository with xml in/out objects
		:return:
		"""
		vc_in = repository.getXmlInputObject(repository.cluster)
		vc_out = repository.getXmlOutputObject()

		vc_out.set_key(key)

		#(fe_template, compute_template) = self.find_templates(vc_in)
		(fe_template, compute_template) = ("biolinux-frontend-cloudstack", "biolinux-compute-cloudstack")

                allocation = self.cloudstackcall.allocateVirtualCluster(fe_template, 1, compute_template, cpus)
		fe_ids = allocation.pop(0)
                response = self.cloudstackcall.listVirtualMachines(None, fe_ids["id"])
		fe = response["virtualmachine"][0]

		ips, macs, cpus_per_node = {}, {}, {}
		vc_out.set_frontend(fe["name"], fe["nic"][1]["ipaddress"], fe["nic"][0]["ipaddress"], "%s.aist.jp" % fe["name"]) # change once fqdn added
		ips[fe["name"]] = {"private": fe["nic"][0]["ipaddress"], "public": fe["nic"][1]["ipaddress"]}
		macs[fe["name"]] = {"private": fe["nic"][0]["macaddress"], "public": fe["nic"][1]["macaddress"]}

		compute_nodes = []
		for compute_ids in allocation:
                	response = self.cloudstackcall.listVirtualMachines(None, compute_ids["id"])
			compute = response["virtualmachine"][0]
			compute_nodes.append(compute["name"])
			cpus_per_node[compute["name"]] = compute["cpunumber"]
			ips[compute["name"]] = { "private" : compute["nic"][0]["ipaddress"] }
			macs[compute["name"]] = { "private" : compute["nic"][0]["macaddress"] }

		vc_out.set_compute_nodes(compute_nodes, cpus_per_node)
		# TODO: need to fix gateway and netmask params after public interface is figured out
		vc_out.set_network(macs, ips, fe["nic"][1]["netmask"], fe["nic"][1]["gateway"], fe["nic"][0]["gateway"], "8.8.8.8")
		vc_out.write()

		return 1


	def clean(self, vcname):
		"""
		Unallocate virtual cluster

		:param vcname: Name of virtual cluster to be cleaned
		:return: True if clean was successful, otherwise False
		"""
        	response = self.cloudstackcall.destroyVirtualCluster(vcname)
        	return response

	def deploy(self, repository):
		"""
		Deploy the specified virtual cluster

		:param repository: repository with xml in/out objects
		:return:
		"""
		vc_in = repository.getXmlInputObject(repository.cluster)
		temp_dir = repository.getStagingDir()

		vc_out = repository.getXmlOutputObject()

                # deploy frontend
		frontend = vc_out.get_frontend()
		if not(self.initializeAndStartVM(frontend["name"], str(vc_out))):
			self.logger.error("Unable to deploy frontend %s" % frontend["name"])
			return False
		self.logger.info("Successfully deployed frontend %s" % frontend["name"])
		# deploy computes
		for name in vc_out.get_compute_names():
			compute_vc_out = vc_out.get_compute_vc_out(name)
			if not(self.initializeAndStartVM(name, compute_vc_out)):
				self.logger.error("Unable to deploy compute %s" % name)
				return False
			self.logger.info("Successfully deployed compute %s" % name)


	def initializeAndStartVM(self, name, vc_out):
		updates = {"userdata": base64.b64encode(str(vc_out))}
		vm_id = self.cloudstackcall.getVirtualMachineID(name)
		response = self.cloudstackcall.updateVirtualMachine(vm_id, updates)
		if response is None:
			return False
		info = self.cloudstackcall.startVirtualMachine(vm_id)
		if response is None:
			return False
		return True

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
			self.logger.error("Could not find template %s in Cloudstack" % frontend_templatename)
			return (None, None)
		if compute_template == None:
			self.logger.error("Could not find template %s in Cloudstack" % compute_templatename)
			return (None, None)
		return (frontend_templatename, compute_templatename)


	def listRepository(self, repository = None):
		"""
		Returns list of templates available for instantiating VMs 
		:param: repository unused 

		:return: list 
			
		"""
                templates = []

        	response = self.cloudstackcall.listTemplates()
                count = response['count']
                for i in range(count):
                    d = response['template'][i]
                    templates.append(d['name'])

                return templates 


	def list(self, vcname=None):
		"""
		Return list of virtual machines sorted by cluster with each VM status

		:return: List of strings formatted as "frontend  compute ndoes status'.
			 First string is a header.
		"""

        	response = self.cloudstackcall.listVirtualClusters(vcname)
		header = pragma.utils.getListHeader(response)
		response.insert(0, header)
        	return response
			

	def shutdown(self, vcname):
		"""
		Shutdown the nodes of the specified virtual cluster.

		:param vcname: Name of running virtual cluster

		:return: An array of virtual machines ordered by cluster 
		 	 each array item has the VM name and its status. 
		"""
        	response = self.cloudstackcall.stopVirtualCluster(vcname)
        	return response


