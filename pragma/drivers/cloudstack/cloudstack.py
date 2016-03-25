#!/usr/bin/env python

import hashlib
import hmac
import base64
import json
import urllib2
import urllib

class CloudStackCall():

    def __init__(self, url, key, secret, templatefilter):
        # initialize from passed arguments
        self.apiUrl = url
        self.apiKey = key
        self.apiSecret = secret
        self.templatefilter = templatefilter
        self.json = 'json'

        #self.request = {}

        # prefix for VM names
        self.vmNamePrefix = 'vm-'

    def buildRequest(self, params):
        self.request = {}
        self.request['response'] = self.json
        self.request['apikey'] = self.apiKey
        for key, value in params.items():
            self.request[key] = value

        self.requestStr = '&'.join(['='.join([k,urllib.quote_plus(self.request[k])]) for k in self.request.keys()])
        self.createSignature()

    def createSignature(self):
        """ Compute the signature with hmac, 
            do a 64 bit encoding and a url encoding:
        """
        sig_str = '&'.join(['='.join([k.lower(),urllib.quote_plus(self.request[k].lower().replace('+','%20'))]) 
                   for k in sorted(self.request.iterkeys())])
        self.sig = hmac.new(self.apiSecret,sig_str,hashlib.sha1)
        self.sig = hmac.new(self.apiSecret,sig_str,hashlib.sha1).digest()
        self.sig = base64.encodestring(hmac.new(self.apiSecret,sig_str,hashlib.sha1).digest())
        self.sig = base64.encodestring(hmac.new(self.apiSecret,sig_str,hashlib.sha1).digest()).strip()
        self.sig = urllib.quote_plus(base64.encodestring(hmac.new(self.apiSecret,sig_str,hashlib.sha1).digest()).strip())
    def sendRequest(self):
        """  build the entire string and do an http GET
        """
        request = self.apiUrl + self.requestStr + '&signature=' + self.sig
        response = urllib2.urlopen(request)
        response_str = response.read()
        response_dict = json.loads(response_str)

        # FIXME check for errors
        return  response_dict[self.request['command'].lower() + 'response']

    def execAPICall(self, command, params = None):
        """ 
        Execute an API call for a command and optional parameters.
            
        :param command: API command name 
        :param params: additional parameters as a dictionary
        :return : an API call response as a dictionary with 2 items
                  1 key = 'count', value = N (number of objects returned)
                  2 key = object name from API request, value = list (length N) 
                          of object's dictionaries 
        """
        comm = {}
        comm['command'] = command
        if params:
            for key, value in params.items():
                comm[key] = value
        self.buildRequest(comm)
        response_dict = self.sendRequest()

        return response_dict

    def listNetworkOfferings(self, name = None):
        command = 'listNetworkOfferings'
        params = {}
        if name:
            params['name'] = name
        response = self.execAPICall(command, params)
        #XXX
        count = response['count']
        for i in range(count):
            d = response['networkoffering'][i]
            print "networkOffering=", d['name'], d['id']

        return response

    def listNetworks(self):
        command = 'listNetworks'
        params = {}
        params['name'] = 'public'
        response = self.execAPICall(command, params)

        return response

    def listTemplates(self, name = None):
        command = 'listTemplates'
        params = {}
        params['templatefilter'] = self.templatefilter
        if name:
            params['name'] = name
        response = self.execAPICall(command, params)

        return response


    def listVirtualMachines(self, name = None, id = None):
        command = 'listVirtualMachines'
        params = {}
        if name:
            params['name'] = name
        if id:
            params['id'] = id
        response = self.execAPICall(command)

        #XXX
        #count = response['count']
        #for i in range(count):
        #    d = response['virtualmachine'][i]
        #    print "id", d

        return response

    def listServiceOfferings(self):
        command = 'listServiceOfferings'
        response = self.execAPICall(command)
        return response

    def getVirtualMachineIPs(self, id = None):
        """
        Returns a list of IPs for the Virtual Machine instances

        :return:  list of IPs 
        """
        response = self.listVirtualMachines(id)
        if not response:
           print "error: no Virtual Machine found" 
           return
        ips = []
        count = response['count']
        for i in range(count):
            d = response['virtualmachine'][i]
            # FIXME : need to deal with multiple nics
            nic = d['nic'][0]
            ips.append(nic['ipaddress'])
            #XXXprint nic['networkname']
        return ips

    def getVirtualMachineID(self, name):
        response = self.listVirtualMachines(name)
        if not response:
           print "error: no Virtual Machine %s found" % name
           return

        ids = []
        count = response['count']
        for i in range(count):
            d = response['virtualmachine'][i]
            if d['name'] == name:
                ids.append(d['id'])

        return ids

    def getNetworkOfferingsID(self, name):
        response = self.listNetworkOfferings(name)
        if not response:
           print "error: no Network Offering name  %s found" % name
           return

        count = response['count']
        for i in range(count):
            d = response['networkoffering'][i]
            if d['name'] == name:
                id = (d['id'])
				break

        return id

    def getTemplateZoneIds(self, name):
        templateId = None
        zoneid = None
        res = self.listTemplates(name)
        if not res:
           print "error: no template found"

        templateId = res['template'][0]['id']
        zoneId = res['template'][0]['zoneid']

        return (templateId, zoneId)

    def getServiceOfferingID(self, ncpu):
        id = None
        def getKey(item):
            return item[0]

        services = self.listServiceOfferings()
        count = services['count']
        all = []
        for i in range(count):
            d = services['serviceoffering'][i]
            all.append((int(d['cpunumber']), d['id']))
        alls = sorted(all, key=getKey)

        for i in alls:
            if i[0] < ncpu:
                continue
            else:
                id = i[1]
                break

        return id

    def getFreeIP(self):
        """
        Find IPs of the existing Virtual Machines
        and return a tuple of next free IP address (str) 
        and its last octet (int)
        :return : a tuple (IP, octet)
        """
        lastoctet = 255
        
        octets = []
        subnet = None
        ips = self.getVirtualMachineIPs()
        for i in ips:
            answer = i.rsplit('.', 1)
            octets.append(int(answer[1]))
            subnet = answer[0]
        octets.sort()

        if not octets:
            print "No IP available"
            return (None, None)

        #FIXME check for ip range
        octet = octets[0] + 1
        while (octet in octets):
            octet = octet + 1
            print octet
        ipaddress = "%s.%d" % (subnet, octet)
        if ipaddress >= lastoctet:
            print "No IP available"
            return (None, None)
        
        return (ipaddress, octet)


    def allocateVirtualCluster(self, feTmpl, fecpu, computeTmpl, ccpu, num):
        """
        Allocate Virtual cluster

        :param feTmpl: template for frontend 
        :param fecpu: number of cpus for FE
        :param computeTmpl: template for compute 
        :param ccpu: number of cpus per compute node
        :param num: number of compute nodes
        """

        allocation = []
        # allocate frontend VM
        ip, octet = self.getFreeIP()
        if not ip:
            print "No free IP is available"
            return allocation

        name = "%s%d" % (self.vmNamePrefix, octet)
        res = self.allocateVirtualMachine(fecpu, feTmpl, name, ip)
        allocation.append(res)

        # allocate compute nodes 
        for i in range(num):
            name = "%s%d-compute-%d" % (self.vmNamePrefix, octet, i)
            print "name", name
            res = self.allocateVirtualMachine(ccpu, computeTmpl, name)
            allocation.append(res)

        return allocation


    def allocateVirtualMachine(self, ncpu, templatename, name, ip = None):
        command = 'deployVirtualMachine'

        # find required parameters for API call
        error = 0
        soid = self.getServiceOfferingID(ncpu)
        if soid is None:
            print "Insufficient resources: service offering does not match request"
            error = 1
        tid, zid = self.getTemplateZoneIds(templatename)
        if tid  is None or zid is None:
            print "Template for virtual machine %s not found" % templatename
            error = 1
        if error:
           print "Unable to allocate virtual machine from template %s" % templatename

        params = {}
        params['name'] = name
        params['serviceofferingid'] = soid
        params['templateid'] = tid
        params['zoneid'] = zid
        params['startvm'] = 'false'

        if ip:
            params['ipaddress'] = ip

        response = self.execAPICall(command, params)
        print response
#{u'id': u'3fc35908-7d76-4bf8-a28e-ea3bf568fdea', u'jobid': u'fc398295-02b9-4d91-bfd6-22c8479d5047'}

        return response

    def deployVirtualMachine(self, ncpu, name):
        pass
        
    def stopVirtualMachine(self, name):
        """ 
        Stop virtual machine given its name
        :param name: Virtual Machine name 
        :return : an API call response as a dictionary with 1 item
                  key = name, value = jobid (for stop call) 
        """ 
        command = 'stopVirtualMachine'

        stopped = {}
        ids = self.getVirtualMachineID(name)
        print "ids", ids
        for id in ids:
            params = {}
            params['id'] = id
            response = self.execAPICall(command, params)
            stopped[name] = response['jobid']

        return stopped

### Main ###

apikey    = 'nWcPrqXC60UAfHyRqXsqm-JZPTHiCIQmMGO0eSp5_GyO9-0p51qC05a7xpgvtVAC1CM-yK4rGB_'
secretkey = 'Y5kSgRBn70NpGRSlmeL9ea6lkZj1fn77VRZKZxz0GkXjrwl86fW72mY5OxE2SAlqX3sudIVe1ZY'
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


