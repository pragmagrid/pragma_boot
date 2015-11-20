import logging
import pragma
from pragma.drivers.kvm_rocks.image_manager import ImageManager
import math
import os
import re
import socket

logger = logging.getLogger('pragma.drivers.kvm_rocks')

class Driver(pragma.drivers.Driver):
	def __init__(self):
		"""

		:return:
		"""
		self.default_memory = 2048
		logger.debug("Loaded driver %s" % self.__class__.__module__)
		(out, exitcode) = pragma.utils.getOutputAsList(
			"rocks list host interface")
		self.used_ips = []
		self.used_vlans = []
		ip_pat = re.compile("(\d+\.\d+\.\d+\.\d+)")
		vlan_pat = re.compile("vlan(\d+)")
		for interface in out:
			result = ip_pat.search(interface)
			if result:
				self.used_ips.append(result.group(1))
			result = vlan_pat.search(interface)
			if result:
				self.used_vlans.append(int(result.group(1)))	

	def allocate(self, cpus, memory, key, vc_in, vc_out, repository):

		"""

getAttributeFromVCfile() {
  vc_in=$1
  nodetype=$2
  attribute=$3

  echo "cat /vc/${nodetype}/domain/devices/disk/source/@${attribute}" | xmllint --shell $vc_in | grep = | awk -F \" '{print $2}'
}

configureNewZfsHost() {
  vc_in=$1
  nodetype=$2
  host=$3

  phy_frontend=`rocks list host attr  localhost | grep Frontend | cut -f 1 -d:`
  disk_volume=`getAttributeFromVCfile $vc_in $nodetype "volume"`
  disk_pool=`getAttributeFromVCfile $vc_in $nodetype "pool"`
  disk_host=`getAttributeFromVCfile $vc_in $nodetype "host"`

  clonename="tmpclone$$"
  ssh $disk_host zfs snapshot $disk_volume@${clonename}
  ssh $disk_host zfs clone $disk_volume@${clonename} $disk_pool/${host}-vol
  rocks set host vm nas $host nas=$disk_host zpool=$disk_pool
  rocks add host storagemap $disk_host $disk_pool ${host}-vol ${phy_frontend} 10
}

if [ "x$#" != "x5" ]; then
    echo "This script should be invoked with 5 arguments"
    exit 1
fi

function error(){
    echo -e "Error $1"
    exit 1
}

# tree required arguments
numcpus=$1
vc_in=$2
vc_out=$3
temp_directory=$4
key=$5

# handle zfs volumes
fe_disk_volume=`getAttributeFromVCfile $vc_in "frontend" "volume"`
comp_disk_volume=`getAttributeFromVCfile $vc_in "compute" "volume"`
if [ "$fe_disk_volume" != "" -a "$comp_disk_volume" != "" ]; then
  configureNewZfsHost $vc_in  "frontend" $fe_hostname
  for h in $cnodes; do
    configureNewZfsHost $vc_in "compute" $h
  done
fi
		:return:
		"""
		(num_nodes, cpus_per_node) = self.calculate_num_nodes(cpus)

		# Load network configuration and import values
                #   public_ips, netmask, gw, dns, fqdn, vlans, diskdir
                #   repository_class, repository_dir, repository_settings

		net_conf = os.path.join(
			os.path.dirname(__file__), "net_conf.conf")
		logger.info("Loading network information from %s" % net_conf)
		execfile(net_conf, {}, globals())
		vc_out.set_key(key)

		# get free ip and vlan
		#(our_ip, our_fqdn) = self.find_free_ip(public_ips)
		(our_ip, our_fqdn) = ("67.58.53.62", "lima-vc-0.sdsc.optiputer.net")
		fe_name = our_fqdn.split(".")[0]
		#our_vlan = self.find_free_vlan(vlans)
		our_vlan = 14
		if not memory:
			memory = self.default_memory

		cmd = "/opt/rocks/bin/rocks add cluster %s %i cpus-per-compute=%i mem-per-compute=%i fe-name=%s cluster-naming=true vlan=%i" % (our_ip, num_nodes, cpus_per_node, memory, fe_name, our_vlan)
		logger.debug("Executing rocks command '%s'" % cmd)
#		(out, exitcode) = pragma.utils.getOutputAsList(cmd)
#		cnodes = []
#		cnode_pat = re.compile("created compute VM named: (\S+)")
#		for line in out:
#			result = cnode_pat.search(line)
#			if result:
#				cnodes.append(result.group(1))
		cnodes = ['vm-lima-vc-0-0', 'vm-lima-vc-0-1']
		vc_out.set_frontend(fe_name, our_ip, our_fqdn)
		vc_out.set_compute_nodes(cnodes, cpus_per_node)
		(macs,ips) = self.get_network(fe_name,cnodes)
		vc_out.set_network(macs,ips, netmask, gw, dns)
		vc_out.set_kvm_diskdir(diskdir)
		vc_out.write()


	def calculate_num_nodes(self, cpus_requested):
		"""
		Calculate the number of nodes and cpus per node to request

		:param cpus_requested: Total number of cpus in virtual cluster
		:return: a tuple (numnodes, cpus_per_node) based on number of 
			cpus available in vm-containers
		"""
		(out, exitcode) = pragma.utils.getOutputAsList(
			"rocks list host vm-container")
		if len(out) < 2:
			logger.error("No vm containers found")
			return -1
		# assume vm containers are uniform so just cpu count from first
		cpu_pat = re.search(" (\d+) ", out[1])
		if not cpu_pat:
			logger.error("Unable to find cpu count of vm container")
			return -1
		vm_container_cpu_count = float(cpu_pat.group(1))
		numnodes = math.ceil(cpus_requested / vm_container_cpu_count)
		return (int(numnodes), 
			int(min(vm_container_cpu_count, cpus_requested)))

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
			logger.error("No available public IPs")
			return None
		# just grab first one in list
		our_ip = avail_ips[0]
		(our_fqdn, our_aliases, addl_ips) = socket.gethostbyaddr(our_ip)
		logger.info("Found available public IP %s -> %s" % (
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
			logger.error("No available vlans")
			return None
		return avail_vlans[0]
 
	def get_network(self, frontend, compute_nodes):
		(out, exitcode) = pragma.utils.getOutputAsList(
			"rocks list host interface")
		macs = { frontend:{} } 
		ips = { frontend:{} }
		for node in compute_nodes:
			macs[node] = {}
			ips[node] = {}
		mac_pat = re.compile("^(\S*%s\S*):\s+(\S+)\s+\S+\s+(\S+)\s+(\S+)" % frontend)
		for line in out:
			result = mac_pat.search(line)
			if result:
				network_type = result.group(2)
				if network_type  == '-------':
					network_type = 'private'
				macs[result.group(1)][network_type] = result.group(3)
				ips[result.group(1)][network_type] = result.group(4)

		return (macs,ips)

	def boot(self, vc_out):
		allnodes = [vc_out.get_frontend()['name']] + \
				vc_out.get_compute_names()
		for node in allnodes:
			(out, exitcode) = pragma.utils.getRocksOutputAsList(
				"set host boot %s action=os" % node )
			if exitcode != 0:
				logger.error("Error setting boot on %s: %s" % (
					node, "\n".join(out)))
				continue
			(out, exitcode) = pragma.utils.getRocksOutputAsList(
				"start host vm %s" % node )
			if exitcode != 0:
				logger.error("Problem booting %s: %s" % (
					node, "\n".join(out)))
		


	def prepare_images(self, vc_in, vc_out, temp_dir):
		network_conf = [
			'/etc/udev/rules.d/70-persistent-net.rules',
			'/etc/sysconfig/network-scripts/ifcfg-eth*'
		]
		new_config = {
			vc_out.filename: "/root/vc-out.xml"
		}
		image_manager = ImageManager.factory(vc_in, vc_out, temp_dir)
		#image_manager.copy_frontend_disk()
		#compute_img_copy = image_manager.create_compute_disk()
		compute_img_copy = "/state/partition1/temp/pragma-Kfr02V3292-2015-11-20/compute.img"
		fe_mnt = image_manager.mount_image(
			image_manager.disks[image_manager.fe_name])
		compute_mnt = image_manager.mount_image(compute_img_copy)
		image_manager.install_to_image(fe_mnt, new_config)
		for mnt in [fe_mnt, compute_mnt]:
			image_manager.safe_remove_from_image(mnt, network_conf)
		for node in vc_out.get_compute_names():
			compute_config = { 
				vc_out.get_vc_out(node): "/root/vc-out.xml"
			}
			image_manager.install_to_image(
				compute_mnt, compute_config)
			#image_manager.scp_image(compute_img_copy, node)
		for mnt in [fe_mnt, compute_mnt]:
			image_manager.umount_image(mnt)

