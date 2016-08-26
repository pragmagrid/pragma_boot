import logging
import pragma
import pragma.utils
from pragma.drivers.kvm_rocks.image_manager import ImageManager
import math
import os
import re
import socket
import subprocess
import sys
import time


class Driver(pragma.drivers.Driver):
	def __init__(self, basepath):
		pragma.drivers.Driver.__init__(self, basepath)
		self.setModuleVals()

		self.default_memory = 2048
		self.logger.debug("Loaded driver %s" % self.__class__.__module__)
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
			"list host interface")
		self.public_ips = {}
		self.used_ips = []
		self.used_vlans = []
		used_vlans = {}
		ip_pat = re.compile("^(\S+):.*?(\d+\.\d+\.\d+\.\d+)")
		vlan_pat = re.compile("\d\d:\d\d:.*\s+(\d+)\s+\-+\s+\-+$")
		for interface in out:
			result = ip_pat.search(interface)
			if result:
				self.public_ips[result.group(1)] = result.group(2)
				self.used_ips.append(result.group(2))
			result = vlan_pat.search(interface)
			if result:
				used_vlans[int(result.group(1))] = 1
		self.used_vlans = used_vlans.keys()

	def allocate(self, cpus, memory, key, enable_ent, repository):
		"""
		Allocate a new virtual cluster from Rocks

		:param cpus: Number of CPUs to instantiate
		:param memory: Amount of memory per compute node
		:param key: Path to SSH Key to install
		:param enable_ent: Boolean to add ENT interfaces to nodes
		:param repository: repository with xml in/out objects
		:return:
		"""
                vc_in = repository.getXmlInputObject(repository.cluster)
                vc_out = repository.getXmlOutputObject()

		# Load network configuration and import values:
		# public_ips, netmask, gw, dns, fqdn, vlans, diskdir, container_hosts, ent
		self.logger.info("Loading network information from %s" % self.driverconf)
		execfile(self.driverconf, {}, globals())

		leave_processors = 0
		try:
			leave_processors = num_processors_reserved
		except:
			pass
		container_hosts = None
		try:
			container_hosts = available_containers
		except:
			pass

		containers_needed = self.calculate_num_nodes(cpus, container_hosts, leave_processors)
		pragma_ent = None
		try:
			pragma_ent = ent
		except:
			pass

		vc_out.set_key(key)

		# get free ip and vlan
		(our_ip, our_fqdn) = self.find_free_ip(public_ips)
		if (our_ip is None):
			 return 0

		fe_name = our_fqdn.split(".")[0]
		our_vlan = self.find_free_vlan(vlans)
		if our_vlan is None:
			return 0

		if not memory:
			memory = self.default_memory
		
		container_hosts_string = "container-hosts=\"%s\"" % " ".join(containers_needed.keys())
		cmd = "/opt/rocks/bin/rocks add cluster %s %i cpus-per-compute=1 mem-per-compute=%i fe-name=%s cluster-naming=true vlan=%i %s" % (our_ip, len(containers_needed), memory, fe_name, our_vlan, container_hosts_string)
		self.logger.debug("Executing rocks command '%s'" % cmd)
		(out, exitcode) = pragma.utils.getOutputAsList(cmd)
		cnodes = []
		cnode_pat = re.compile("created compute VM named: (\S+)")
		for line in out:
			result = cnode_pat.search(line)
			if result:
				cnodes.append(result.group(1))
		if enable_ent and pragma_ent != None:
			self.configure_ent(pragma_ent, [fe_name] + cnodes)
			
		phy_hosts = self.get_physical_hosts(fe_name)
		cpus_per_node = {}
		for node in cnodes:
			(out, exitcode) = pragma.utils.getRocksOutputAsList(
				"set host cpus %s %d" % (node, containers_needed[phy_hosts[node]]))
			cpus_per_node[node] = containers_needed[phy_hosts[node]]

		self.logger.info("Allocated cluster %s with compute nodes: %s" % (fe_name, ", ".join(cnodes)))

		(macs,ips, priv_ip, priv_netmask) = self.get_network(fe_name, cnodes)
		vc_out.set_frontend(fe_name, our_ip, priv_ip, our_fqdn)
		vc_out.set_compute_nodes(cnodes, cpus_per_node)
                vc_out.set_network(macs, ips, netmask, priv_netmask, gw, priv_ip, "8.8.8.8")

		try:
			vc_out.set_kvm_diskdir(diskdir)
		except:
			pass

		vc_out.write()

		return 1


	def boot(self, node):
		"""
		Boot the specified Rocks node

		:param node: Name of Rocks node
		:return:
		"""
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
			"set host boot %s action=os" % node )
		if exitcode != 0:
			self.logger.error("Error setting boot on %s: %s" % (
				node, "\n".join(out)))
			return
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
			"start host vm %s" % node)
		if exitcode != 0:
			self.logger.error("Problem booting %s: %s" % (
				node, "\n".join(out)))

	def calculate_num_nodes(self, cpus_requested, available_containers, num_processors_reserved):
		"""
		Calculate the number of nodes and cpus per node to request

		:param cpus_requested: Total number of cpus in virtual cluster
		:param available_containers: List of container names we can use
		:param num_processors_reserved: Leave some CPUs for OS

		:return: a hash array where key is the container name and value
		is the number of cpus to use
		"""

		self.logger.info("Requesting %i CPUs" % cpus_requested)
		container_capacity = self.get_container_capacity()

		# filter out containers and processors we can't use
		for container in container_capacity:
			container_capacity[container] -= num_processors_reserved
			if available_containers is not None and available_containers.index(container) < 0:
				container_capacity.delete(container)

		# remove cpus used
		container_usage = self.get_container_usage()
		for container in container_usage:
			if container in container_capacity:
				container_capacity[container] -= container_usage[container]

		# sort available containers by capacity and then name
		most_available = sorted(container_capacity, key=lambda container: (
		        container_capacity[container],
		        int(container.split('-')[-1])*100 + int(container.split('-')[-2])))

		# allocate cluster to resources with most capacity
		cpus_allocated = 0
		containers_needed = {}
		while cpus_allocated < cpus_requested and len(most_available) > 0:
			container = most_available.pop()
			cpus_needed = cpus_requested - cpus_allocated
			cpus_from_host = min(container_capacity[container], cpus_needed)
			containers_needed[container] = cpus_from_host
			cpus_allocated += container_capacity[container]

		if cpus_allocated < cpus_requested:
			self.logger.error("There is not enough capacity to fulfill your request of %i cpus" % cpus_requested)
			print "Error: There is not enough capacity to fulfill your request of %i cpus" % cpus_requested
			sys.exit(1)
		return containers_needed


	def clean(self, vcname):
		"""
		Unallocate virtual cluster and clean up disks.

		:param vcname: Name of virtual cluster to be cleaned
		:return: True if clean was successful, otherwise False
		"""
		nodes = self.get_cluster_status(vcname)
		for node in nodes:
			if nodes[node] == 'active':
				sys.stderr.write("Error: node %s still active; please shutdown cluster first.\n" % node)
				return False
		for node in nodes:
			(out, exitcode) = pragma.utils.getRocksOutputAsList(
				"list host vm %s showdisks=true" % node)
			if exitcode != 0:
				sys.stderr.write("Problem quering node %s: %s\n" % (
					node, "\n".join(out)))
				return False
			fields = re.split("\s+", out[1])

			if ImageManager.clean_disk(node, fields[6], fields[4]) == False:
				sys.stderr.write("Problem cleaning disk of node %s\n" % node)
				return False

		print "  Unallocating cluster %s" % vcname
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
			"remove cluster %s" % vcname)
		for line in out:
			print "  %s" % line
		return True

	def configure_ent(self, ent_info, nodes):
		"""
		Add ENT interface to specified virtual nodes

		:param ent_info: config information for PRAGMA-ENT
		:param nodes: array of virtual node names
		:return: True if successful; otherwise False
		"""
		for node in nodes:
			(out, exitcode) = pragma.utils.getRocksOutputAsList(
				"report vm nextmac")
			if out == None or len(out) < 1:
				self.logger.error("Unable to get mac address for %s" % node)
				return False
			mac = out[0]
			(out, exitcode) = pragma.utils.getRocksOutputAsList(
				"add host interface %s %s subnet=%s mac=%s" % (
				node, ent_info['interface_name'], ent_info['subnet_name'], mac))
			if exitcode != 0:
				self.logger.error("Unable to add interface to %s" % node)
				return False
			(out, exitcode) = pragma.utils.getRocksOutputAsList(
				"sync host network %s" % node)
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
				"sync config")

	def deploy(self, repository):
		"""
		Deploy the specified virtual cluster

		:param repository: repository with xml in/out objects
		:return:
		"""
		# get references to xml in/out objects and temp directory 
		vc_in = repository.getXmlInputObject(repository.cluster)
		vc_out = repository.getXmlOutputObject()
		temp_dir = repository.getStagingDir()

		network_conf = [
			'/etc/udev/rules.d/70-persistent-net.rules',
			'/etc/sysconfig/network-scripts/ifcfg-eth*'
		]
		new_config = {
			vc_out.filename: "/root/vc-out.xml"
		}
		image_manager = ImageManager.factory(vc_in, vc_out, temp_dir)

		# prepare and boot frontend
		image_manager.prepare_frontend(network_conf, new_config)
		self.boot(image_manager.fe_name)

		# prepare and boot computes
		for node in vc_out.get_compute_names():
			compute_config = {
				vc_out.get_vc_out(node): "/root/vc-out.xml"
			}
			image_manager.prepare_compute(node, network_conf, compute_config)
			self.boot(node)
		image_manager.boot_cleanup()

	def find_free_ip(self, avail_ips):
		"""
		Find a free public ip address from avail ips

		:param avail_ips: List of public IP addresses
		:return: a tuple (ip, fqdn) representing a free ip address
		"""
		for ip in self.used_ips:
			try:
				avail_ips.remove(ip)
			except:
				pass

		if len(avail_ips) < 1:
			self.logger.error("No available public IPs")
			print "Error: No available public IPs"
			return (None, None)

		# just grab first one in list
		our_ip = avail_ips[0]
		(our_fqdn, our_aliases, addl_ips) = socket.gethostbyaddr(our_ip)
		self.logger.info("Found available public IP %s -> %s" % (
			our_ip, our_fqdn))
		return (our_ip, our_fqdn)

	def find_free_vlan(self, avail_vlans):
		"""
		Find a free vlan from range of vlans

		:param avail_vlans: List of available vlan ids
		:return: an integer representing a free vlan id
		"""
		for vlan in self.used_vlans:
			try:
				avail_vlans.remove(vlan)
			except:
				pass
		if len(avail_vlans) < 1:
			self.logger.error("No available vlans")
			print "Error: No available vlans"
			return None
		return avail_vlans[0]

	def get_container_capacity(self):
		"""
		Return the CPU capacity of the physical VM containers

		:return:  Hash array where key is container name and value is 
		CPU capacity
		"""
		container_capacity = {}
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
			"list host vm-container")
		cpu_pat = re.compile("([^:]+):[^\d]+(\d+)\s+\d+\s+\d+")
		for line in out:
			result = cpu_pat.search(line)
			if result is not None:
				container_capacity[result.group(1)] = int(result.group(2))
		return container_capacity

	def get_container_usage(self):
		"""
		Return the CPU usage of the physical VM containers

		:return:  Hash array where key is container name and value is 
		CPU usage
		"""
		container_usage = {}
		cpu_pat = re.compile("(\d+)\s+[^:][^:]:\S+\s+(vm-container\S+).*active\s*$")
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
			"list host vm status=true")
		for line in out:
			result = cpu_pat.search(line)
			if result is None:
				continue
			if result.group(2) in container_usage:
				container_usage[result.group(2)] += int(result.group(1))
			else:
				container_usage[result.group(2)] = int(result.group(1))
		return container_usage

	def get_cluster_status(self, vcname):
		"""
		Return whether the virtual cluster nodes are active or inactive

		:param vcname: Virtual cluster defined in Rocks DB

		:return:  Hash array indicating the virtual cluster node status where
		the key is the node and the value is the status.
		"""
		nodes = {}
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
			"list cluster status=true %s" % vcname)
		if exitcode != 0:
			sys.stderr.write("Error quering cluster %s: %s\n" % (
				vcname, "\n".join(out)))
			sys.exit(1)
		out.pop(0) # remove column headers
		result = re.search("^([^:]+):\s+\S+\s+\S+\s+(\S+)", out.pop(0))
		nodes[result.group(1)] = result.group(2)
		for line in out:
			result = re.search("^\s*:\s+(\S+)\s+\S+\s+(\S+)", line)
			if result is not None:
				nodes[result.group(1)] = result.group(2)
		return nodes

	def get_network(self, frontend, compute_nodes):
		"""
		Get network information for newly instantiated virtual cluster

		:param frontend: Name of virtual cluster frontend
		:param compute_nodes: Array of virtual cluster compute nodes
		:return:  Array of mac and ip addresses
		"""
		(out, exitcode) = pragma.utils.getOutputAsList(
			"rocks list host interface")
		macs = {frontend:{}}
		ips = {frontend:{}}
		for node in compute_nodes:
			macs[node] = {}
			ips[node] = {}
		mac_pat = re.compile("^(\S*%s\S*):\s+(\S+)\s+\S+\s+(\S+)\s+(\S+)\s+(\S+)" % frontend)
		priv_ip = None
		priv_netmask = None
		for line in out:
			result = mac_pat.search(line)
			if result:
				node_name = result.group(1)
				network_type = result.group(2)
				if re.search("[\-]+", network_type) is not None: 
					network_type = 'private'
				if node_name == frontend and network_type == 'private':
					priv_ip = result.group(4)
					priv_netmask = result.group(5)
				macs[node_name][network_type] = result.group(3)
				ips[node_name][network_type] = result.group(4)

		return (macs,ips, priv_ip, priv_netmask)

	def get_physical_hosts(self, vcname):
		"""
		Return the physical hosts of the specified virtual cluster

		:return: Hash array where the key is the virtual node name and
			value is the physical host
		"""
		phy_hosts = {}
		(out, ec) = pragma.utils.getRocksOutputAsList(
				"list host vm")
                host_pat = re.compile("^(\S*%s\S*):\s+\d+\s+\d+\s+\d+\s+\S+\s+(\S+)" % vcname)
                for line in out:
                        result = host_pat.search(line)
                        if result:
                                phy_hosts[result.group(1)] = result.group(2)
		return phy_hosts

	def list(self, *argv):
		"""
		Return list of virtual machine sorted by cluster with each VM status

		:return: List of strings formatted as "frontend  compute ndoes status'.
			 First string is a header 
		"""

		rockscmd = None
		if len(argv) == 0:
			rockscommand = "list cluster status=1"
		else:
			vcname = argv[0]
			rockscommand = "list cluster %s status=1" % vcname

		(out, exitcode) = pragma.utils.getRocksOutputAsList(rockscommand)
		if exitcode != 0:
			sys.stderr.write("Problem quering clusters: %s\n" % ( "\n".join(out)))
			return [] 

		clusters = []
		pat = ' VM' # search for this pattern in the output
		for line in out:
			if line.find(pat) < 0 : # don't include physical nodes
				continue
			clusters.append(line)

		# remove pattern ' VM    ' from the output
		clusters = [s.replace(pat + '    ', '') for s in clusters]

		# insert public IP addresses
		fe_pat = re.compile("^(\S+):")
		for i,line in enumerate(clusters):
			ip = '-'*pragma.utils.IP_ADDRESS_LEN
			result = fe_pat.search(line)
			if result:
				ip = self.public_ips[result.group(1)]
			clusters[i] = "%s  %s" % (clusters[i],ip) 

		# add listing header
		header = pragma.utils.getListHeader(clusters)
		clusters.insert(0, header)

		return clusters


	def listRepository(self, repository):
		 return  repository.listRepository()


	def shutdown(self, vcname):
		"""
		Shutdown the nodes of the specified virtual cluster.

		:param vcname: Name of running virtual cluster

		:return: True if cluster is shutdown, otherwise False
		"""

		nodes = self.get_cluster_status(vcname)
		for node in nodes:
			if nodes[node] == 'active':
				print "  Shutting down node %s" % node
				exitcode=0
				(out, exitcode) = pragma.utils.getRocksOutputAsList(
					"stop host vm %s" % node)
				if exitcode != 0:
					sys.stderr.write("Problem shutting down node %s: %s\n" % (
						node, "\n".join(out)))
					sys.exit(1)
				time.sleep(1)
		nodes = self.get_cluster_status(vcname)
		disks = ImageManager.get_disks(vcname)
		for node in nodes:
			if nodes[node] != 'nostate':
				sys.stderr.write("Error, node %s not shut down\n" % node)
				return False
			ImageManager.wait_for_disk(vcname, disks[vcname])
		return True
		


