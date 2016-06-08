#!/usr/bin/env python

# user  apikey and secret key are in the file mykeys.py
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
        for n in range(numnics):
            nic = d['nic'][n]
            print "VMs:", d["name"], nic['ipaddress'], nic['networkname']

def GetIPs ():
    ips = apicall.getVirtualMachineIPs()
    print ips

#apicall.allocateVirtualCluster("biolinux-frontend-original",1,"biolinux-compute-original",1,2)

#apicall.listServiceOfferings()
#apicall.allocateVirtualMachine(1, "biolinux-compute-original")

############## tested ok ############## 
#ListNetworks()

#ListTemplates()
#name = 'biolinux-frontend-original'
#ListTemplates(name)

#ListNetworkOfferings()
#ListNetworkOfferings(networkoffering)

#ListVMs()
# when giving a name, the outputcontains all vms with the name substring
#ListVMs(name = 'vm-48-compute-1')

#GetIPs()
