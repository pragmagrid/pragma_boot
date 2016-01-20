import logging
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

logger = logging.getLogger('pragma.conf')

class VcIn:
	def __init__(self, xmltree, dir):
		self.xml = xmltree
		self.dir = dir
		
	def get_arch(self):
		virt =  self.xml.find("virtualization")
		if virt != None:
			return virt.attrib['arch']
		else:
			logger.error("Unable to find virtualization tag")
			return None

	def get_disk(self, node):
		disk = self.xml.find("%s/domain/devices/disk/source" % node)
		if disk != None:
			return disk.attrib
		else:
			logger.error("Unable to find disk for node %s" % node)
			return None

class VcOut:

	def __init__(self, filename):
		self.filename = filename
		self.compute_nodes = {}

	def __str__(self):
		vc = ET.Element('vc')

		frontend = ET.SubElement(vc, 'frontend')
		ET.SubElement(frontend, 'public', attrib = { 
			'netmask':self.netmask,
			'gw':self.gateway,
			'fqdn':self.frontend['fqdn'],
			'ip':self.frontend['ip'],
			'mac':self.macs[self.frontend['name']]['public'],
			'name':self.frontend['name']})
		ET.SubElement(frontend, 'private', attrib = { 
			'netmask':'255.255.0.0',
			'ip':'10.1.1.1',
			'mac':self.macs[self.frontend['name']]['private']})

		computes = ET.SubElement(vc, 'compute', attrib = {'count':str(len(self.compute_nodes))})
		for node in self.compute_nodes:
			ET.SubElement(computes, 'node', attrib = { 
			'name':self.compute_nodes[node]['name'],
			'ip':self.compute_nodes[node]['ip'],
			'mac':self.macs[node]['private'],
			'cpus':str(self.cpus_per_node)})
		self.append_network_key(vc)
		return self.prettify(vc)

	def append_network_key(self, vc):
		network = ET.SubElement(vc, 'network')
		ET.SubElement(network, 'dns', attrib = { 
			'ip':self.dns, 'search':"local", 'domain':""})
		key = ET.SubElement(vc, 'key')
		key.text = self.key

	def clean(self):
		if os.path.exists(self.filename):
			os.remove(self.filename)
		for node in self.compute_nodes:
			if os.path.exists(self.compute_nodes[node]['vc_out']):
				os.remove(self.compute_nodes[node]['vc_out'])

	def get_compute_names(self):
		return sorted(self.compute_nodes.keys())

	def get_frontend(self):
		return self.frontend 

	def get_kvm_diskdir(self):
		return self.kvm_diskdir 

	def get_vc_out(self, node):
		return self.compute_nodes[node]['vc_out']

	def prettify(self, elem):
		"""Return a pretty-printed XML string for the Element.
		"""
		rough_string = ET.tostring(elem, 'utf-8')
		reparsed = minidom.parseString(rough_string)
		return reparsed.toprettyxml(indent="  ")

	def set_frontend(self, name, ip, fqdn):
		self.frontend = {'name':name, 'ip':ip, 'fqdn':fqdn}

	def set_key(self, key):
		file = open(key, "r")
		self.key = file.read()
		file.close()
		self.key = self.key.rstrip("\n")

	def set_kvm_diskdir(self, dir):
		self.kvm_diskdir = dir

	def set_network(self, macs, ips, netmask, gateway, dns):
		self.macs = macs
		self.ips = ips
		self.netmask = netmask
		self.gateway = gateway
		self.dns = dns
		
	def set_compute_nodes(self, compute_nodes, cpus_per_node):
		counter=254
		dir = os.path.dirname(self.filename)
		for node in compute_nodes:
			self.compute_nodes[node] = {}
			self.compute_nodes[node]['ip'] = '10.1.1.%i' % counter
			self.compute_nodes[node]['name'] = 'compute-%i' % (254-counter)
			self.compute_nodes[node]['vc_out'] = os.path.join(dir, "%s.xml" % node)
			counter-=1
		self.cpus_per_node = cpus_per_node

	def write_compute(self, node):
		vc = ET.Element('vc')
		frontend = ET.SubElement(vc, 'frontend')
		ET.SubElement(frontend, 'public', attrib = { 
			'fqdn':self.frontend['fqdn']})
		compute = ET.SubElement(vc, 'compute')
		ET.SubElement(compute, 'private', attrib = { 
			'fqdn':self.compute_nodes[node]['name'],
			'ip':self.compute_nodes[node]['ip'],
			'netmask':'255.255.0.0',
			'gw':'10.1.1.1',
			'mac':self.macs[node]['private']})
		self.append_network_key(vc)
		file = open(self.compute_nodes[node]['vc_out'], "w")
		file.write(self.prettify(vc))
		file.close
		logger.debug("Writing vc-out file to %s" % self.compute_nodes[node]['vc_out'])

	def write(self):
		file = open(self.filename, "w")
		file.write(str(self))
		file.close
		logger.debug("Writing vc-out file to %s" % self.filename)
		for node in self.compute_nodes:
			self.write_compute(node)
