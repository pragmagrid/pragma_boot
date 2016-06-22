#!/usr/bin/env python

# user apikey and secret key are in the file mykeys.py
# do not add mykeys.py to git repo
from mykeys import *
from cloudstack import CloudStackCall

### Main ###
# base settings for the cloudstack configuration
baseurl   = 'http://163.220.56.65:8080/client/api?'
templatefilter = 'community'
networkoffering = 'DefaultIsolatedNetworkOfferingWithSourceNatService'

apicall = CloudStackCall(baseurl, apikey, secretkey, templatefilter)

def ListNetworks ():
    response = apicall.listNetworks()
    print response.keys()
    count = response['count']
    for i in range(count):
        d = response['network'][i]
        print "network:", d['name'], d['id'], d['networkofferingid'], d['cidr'], d['netmask']

def ListTemplates (name = None):
    response = apicall.listTemplates(name)
    count = response['count']
    for i in range(count):
        d = response['template'][i]
        print "template:", d['name'], d['id']

def ListNetworkOfferings(name = None):
    response = apicall.listNetworkOfferings(name)
    # in response  count does not always corresponds to the list length, dont use count = response['count']
    count = len(response['networkoffering'])
    for i in range(count):
        d = response['networkoffering'][i]
        print "networkOffering:", d['name'], d['id']

def ListVMs (name = None, id = None):
    response = apicall.listVirtualMachines(name)
    count = response['count']
    for i in range(count):
        d = response['virtualmachine'][i]
        # deal with multiple nics
        numnics =  len(d['nic'])
        print "VMs:", d["name"], d["id"], d['state']
        for n in range(numnics):
            nic = d['nic'][n]
            print "    %s\t%s\t%s" % (nic['ipaddress'], nic['networkname'], nic['macaddress'])

def ListClusters(name = None):
    response = apicall.listVirtualClusters(name)
    for i in response:
        print i

def GetVCips ():
    ips = apicall.getVirtualMachineIPs()
    print ips

def GetVCids (name):
    ids = apicall.getVirtualMachineID(name)
    print ids

def StopVM(id):
    d = apicall.stopVirtualMachine(id)
    print "keys ", d.keys()
    print "stop vm jobid ",  d['jobid']
    CheckJobResult(d[jobid])

def StopVC(name):
    d = apicall.stopVirtualCluster(name)
    print "return status: ", d

def StartVC(name):
    d = apicall.startVirtualCluster(name)
    for k in  d.keys():
      print "strt vm jobid: ", k,  d[k]
    CheckJobResult(d[k])

def AllocateVM(cpu, template, name):
    response = apicall.allocateVirtualMachine(cpu, template, name)
    print "keys", response.keys()
    count = response['count']
    for i in range(count):
        d = response['virtualmachine'][i]
        # deal with multiple nics
        numnics =  len(d['nic'])
        print "VMs:", d["name"], d["id"], d['state']
        for n in range(numnics):
            nic = d['nic'][n]
            print "    %s\t%s\t%s" % (nic['ipaddress'], nic['networkname'], nic['macaddress'])

def CheckJobResult(id):
	response = apicall.queryAsyncJobResult(id)
	if response:
	    for k in response.keys():
		print "%s\t = %s" % (k, response[k])

def ListAsyncJobs():
	response = apicall.listAsyncJobs()
        count = response['count']
        for i in range(count):
            d = response['asyncjobs'][i]
            for k in d.keys():
                print "%s\t = %s" % (k, d[k])
            print "---------------------" 


##### need to retest ######
#apicall.allocateVirtualCluster("biolinux-frontend-original",1,"biolinux-compute-original",1,2)
#apicall.listServiceOfferings()

#AllocateVM(1, "biolinux-compute-original", "mybio")
############## tested ok ############## 
#ListNetworks()

#ListTemplates()
#name = 'biolinux-frontend-original'
#ListTemplates(name)

#ListNetworkOfferings()
#ListNetworkOfferings(networkoffering)

#ListVMs()
# when giving a name, the outputcontains all vms with the name substring
#ListVMs(name = 'vm-46')

#StopVM('3f309f0b-ebeb-425b-b545-d01090a025a1')
#StopVC('vm-46')

#GetVCips()
#GetVCids('vm-48')
#GetVCids('vm-48-compute-0')

#ListClusters()
#ListClusters('vm-48')

#id = '6a92cd31-f778-4160-b681-8b199d8afff1'
#CheckJobResult(id)

#StartVC('vm-46')

ListAsyncJobs()

