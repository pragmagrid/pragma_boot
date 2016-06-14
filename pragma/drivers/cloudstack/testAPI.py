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

def StopVC(name):
    d = apicall.stopVirtualCluster(name)
    for k in  d.keys():
      print "stop vm jobid: ", k,  d[k]

def StartVC(name):
    d = apicall.startVirtualCluster(name)
    for k in  d.keys():
      print "strt vm jobid: ", k,  d[k]

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

#StopVM('3d543e25-a0c1-45f2-beb0-bde10996f214')
StopVC('vm-48')

#GetVCips()
#GetVCids('vm-48')
#GetVCids('vm-48-compute-0')

#ListClusters()
#ListClusters('vm-48')

#StartVC('vm-48')
