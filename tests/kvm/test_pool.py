#!/usr/bin/python
#
# LC 



import libvirt
import sys
import socket



#if not hostname :
hostname = socket.gethostname().split('.')[0]

connectionURL = 'qemu://%s/system'
trans_pool_name = "transferimages"
tmp_folder = "/state/partition2"


hipervisor = libvirt.open( connectionURL % hostname)

if trans_pool_name not in hipervisor.listStoragePools():
	#create trans pool name
	if not os.path.exists(tmp_folder):
		os.makedirs(tmp_folder)
	pool_creation_xml = "<pool type='dir'><name>%s</name><target><path>%s</path></target></pool>"
	hipervisor.storagePoolCreateXML(pool_creation_xml % (trans_pool_name, tmp_folder), 0)

output_xml = 


# virt-v2v  -f virt-v2v.xml -f /var/lib/virt-v2v/virt-v2v.db -i libvirtxml -oa sparse -os transferimages output.xml
	

# to destroy a storage pool
# hipervisor.storagePoolLookupByName(a[0]).destroy()
# hipervisor.storagePoolLookupByName(a[0]).delete(0)


	





