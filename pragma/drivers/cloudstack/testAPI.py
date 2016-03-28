#!/usr/bin/env python

from cloudstack import CloudStackCall

### Main ###

apikey    = 'nWcPrqXC60UAfHyRqXsqm-JZPTHiCIQmMGO0eSp5_GyO9-0p51qC05a7xpgvtVAC1CM-'
secretkey = 'Y5kSgRBn70NpGRSlmeL9ea6lkZj1fn77VRZKZxz0GkXjrwl86fW72mY5OxE2SAlqX3sudIVe'
baseurl   ='http://163.220.56.65:8080/client/api?'
templatefilter = 'community'
networkoffering = 'DefaultIsolatedNetworkOfferingWithSourceNatService'

apicall = CloudStackCall(baseurl, apikey, secretkey, templatefilter)
#apicall.allocateVirtualCluster("biolinux-frontend-original",1,"biolinux-compute-original",1,2)
apicall.listNetworkOfferings(networkoffering)
apicall.listNetworks()

# tested ok
apicall.listTemplates('biolinux-frontend-original')
#apicall.listVirtualMachines()
#apicall.listServiceOfferings()
#apicall.allocateVirtualMachine(1, "biolinux-compute-original")

