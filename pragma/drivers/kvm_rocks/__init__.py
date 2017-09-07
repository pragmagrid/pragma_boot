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
		ip_pat = re.compile("^(\S+):.*?(\d+\.\d+\.\d+\.\d+)\s+\d")
		vlan_pat = re.compile("(\d+)\s+\-+\s+\-+$")
		for interface in out:
			result = ip_pat.search(interface)
			if result:
				self.public_ips[result.group(1)] = result.group(2)
				self.used_ips.append(result.group(2))
			result = vlan_pat.search(interface)
			if result:
				used_vlans[int(result.group(1))] = 1
		self.used_vlans = used_vlans.keys()

	def add_interfaces(self, networks, add_ifaces, nodes):
		"""
		Add additional interface to specified virtual nodes

		:param networks: hash array of allowed networks for additional interfaces
		where the key is the network name and the value is the name of the device
		:param add_ifaces hash array of additional interfaces where the key is the
		network name and the value is the cidr address if specified
		:param nodes: array of virtual node names
		:return: True if successful; otherwise False
		"""
		for network_name in add_ifaces:
			self.logger.info("Adding %s interfaces to nodes" % network_name)
			for node in nodes:
				(out, exitcode) = pragma.utils.getRocksOutputAsList(
					"report vm nextmac")
				if out == None or len(out) < 1:
					self.logger.error("Unable to get mac address for %s" % node)
					return False
				mac = out[0]
				(out, exitcode) = pragma.utils.getRocksOutputAsList(
					"add host interface %s %s subnet=%s mac=%s" % (
					node, networks[network_name], network_name, mac))
				if exitcode != 0:
					self.logger.error("Unable to add interface to %s" % node)
					return False
				pragma.utils.getRocksOutputAsList(
					"sync host network %s" % node)
				pragma.utils.getRocksOutputAsList(
					"sync config")

	def allocate(self, cpus, memory, key, add_ifaces_spec, repository):
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

		networks = {'public': None, 'private': None}
		try:
			networks.update(additional_interfaces)
		except:
			pass
		add_ifaces = self.parse_user_interfaces(add_ifaces_spec)
		for network_name in add_ifaces:
			if network_name not in networks:
				self.logger.error("Interfaces on network %s not allowed, please specify in 'additional_interfaces' in kvm_rocks.conf file" % network_name)
				return 0

		containers_needed = self.calculate_num_nodes(cpus, container_hosts, leave_processors)

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
		if add_ifaces:
			self.add_interfaces(networks, add_ifaces, [fe_name] + cnodes)
			
		phy_hosts = self.get_physical_hosts(fe_name)
		cpus_per_node = {}
		for node in cnodes:
			(out, exitcode) = pragma.utils.getRocksOutputAsList(
				"set host cpus %s %d" % (node, containers_needed[phy_hosts[node]]))
			cpus_per_node[node] = containers_needed[phy_hosts[node]]

		self.logger.info("Allocated cluster %s with compute nodes: %s" % (fe_name, ", ".join(cnodes)))

		cluster_network = self.get_network(networks, fe_name, our_fqdn, add_ifaces)
		if cluster_network is None:
			return 0
		vc_out.set_network(cluster_network, dns)
		vc_out.set_compute_nodes(cnodes, cpus_per_node)

		try:
			vc_out.set_kvm_diskdir(diskdir)
		except:
			pass

		vc_out.write()

		return 1

	def parse_user_interfaces(self, add_ifaces_spec):
		"""
		Parse the user specified interfaces from the command line

		:param add_ifaces_spec: string containing comma separated list of net:cidr
		values

		:return: A dictionary where the network name is the key and the values
		are an array of Network objects
		"""
		add_ifaces = {}
		if add_ifaces_spec is not None:
			ifaces = re.split("\s*,", add_ifaces_spec)
			for iface in ifaces:
				cidr = None
				if iface.find(":") >= 0:
					(network_name, cidr) = re.split(":", iface)
				else:
					network_name = iface
				if network_name not in add_ifaces:
					add_ifaces[network_name] = []
				(subnet, netmask) = pragma.utils.parse_cidr(cidr)
				add_ifaces[network_name].append(
					pragma.utils.Network(subnet, netmask, None))
		return add_ifaces

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
		time.sleep(15)
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

	def get_network(self, networks, frontend, fqdn, add_ifaces):
		"""
		Get network information for newly instantiated virtual cluster

		:param frontend: Name of virtual cluster frontend
		:param compute_nodes: Array of virtual cluster compute nodes
		:return:  Array of mac and ip addresses
		"""
		cluster_network = pragma.utils.ClusterNetwork(frontend, fqdn)

		# get network info
		(out, exitcode) = pragma.utils.getOutputAsList("rocks list network")
		net_pat = re.compile("^(\S+):\s+(\S+)\s+(\S+)\s+(\S+)")
		for line in out:
			result = net_pat.search(line)
			if result:
				(net_name, subnet, netmask, mtu) = result.groups()
				if net_name in networks:
					cluster_network.add_net(net_name, subnet, netmask, mtu)

		# get interface info
		(out, exitcode) = pragma.utils.getOutputAsList("rocks list host interface")
		iface_pat = re.compile("^(\S*%s\S*):\s+(\S+)\s+\S+\s+(\S+)\s+(\S+)" % frontend)
		for line in out:
			result = iface_pat.search(line)
			if result:
				(node_name, net, mac, ip) = result.groups()
				if net == 'private' and node_name == frontend:
					# IP is relative to physical cluster if exists -- we reset
					# for internal vc
					ip = cluster_network.get_frontend_ip(net)
				if net in add_ifaces:
					for user_net in add_ifaces[net]:
						# overwrite with user specified subnet/netmask
						cluster_network.add_iface(node_name, net, ip, mac, user_net)
				else:
					cluster_network.add_iface(node_name, net, ip, mac)

		# get gateways
		(out, exitcode) = pragma.utils.getOutputAsList("rocks list host route")
		gw_pat = re.compile("^([^:]*%s[^:]*):\s*0.0.0.0\s+0.0.0.0\s+(\S+)" % frontend)
		for line in out:
			result = gw_pat.search(line)
			if result is not None:
				(node, gw) = result.groups()
				cluster_network.add_gw(node, gw)

		return cluster_network

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
		


