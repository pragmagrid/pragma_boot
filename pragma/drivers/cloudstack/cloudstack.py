#!/usr/bin/env python

import hashlib
import hmac
import base64
import json
import urllib2
import urllib
import logging

class CloudStackCall:

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
        # suffix for VM compute nodes names
        self.vmNameSuffix = '-compute-'
        self.setParams()

    def setParams(self):
        self.publicNetworkName = 'public'
        self.privateNetworkName = 'private'
        self.getZoneID()
        self.networkofferingID = self.getNetworkOfferingsID()

        # add public network if none exist
        response = self.listNetworks()
        if not response:
            self.createNetwork(self.publicNetworkName)

    def buildRequest(self, params):
        self.request = {}
        self.request['response'] = self.json
        self.request['apikey'] = self.apiKey
        for key, value in params.items():
            self.request[key] = value

        # create request string
        self.requestStr = ''
        for k in self.request.keys():
            self.requestStr += '='.join([k, urllib.quote_plus(self.request[k])]) + '&'
        self.requestStr = self.requestStr[:-1] # remove last '&'

        self.createSignature()

    def createSignature(self):
        """ Compute the signature with hmac, 
            do a 64 bit encoding and a url encoding:
        """

        # create signature string
        sig_str = ''
        for k in sorted(self.request.iterkeys()):
            sig_str += '='.join([k.lower(),urllib.quote_plus(self.request[k].lower().replace('+','%20'))]) + '&'
        sig_str = sig_str[:-1] # remove last '&'

        # encode signature
        self.sig = hmac.new(self.apiSecret,sig_str,hashlib.sha1)
        self.sig = hmac.new(self.apiSecret,sig_str,hashlib.sha1).digest()
        self.sig = base64.encodestring(hmac.new(self.apiSecret,sig_str,hashlib.sha1).digest())
        self.sig = base64.encodestring(hmac.new(self.apiSecret,sig_str,hashlib.sha1).digest()).strip()
        self.sig = urllib.quote_plus(base64.encodestring(hmac.new(self.apiSecret,sig_str,hashlib.sha1).digest()).strip())

    def getError(self, exception):
        error_response = json.loads(exception.read())
        return error_response[error_response.keys()[0]]["errortext"]

    def sendRequest(self):
        """  build the entire string and do an http GET
        """
        request = self.apiUrl + self.requestStr + '&signature=' + self.sig
        logging.debug("Sending request string: %s" % request)
        response = urllib2.urlopen(request)
        response_str = response.read()
        response_dict = json.loads(response_str)
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
        logging.debug("Sending command %s to Cloudstack" % command)
        comm['command'] = command
        if params:
            for key, value in params.items():
                comm[key] = value
        self.buildRequest(comm)
        response_dict = self.sendRequest()

        return response_dict

    def createNetwork(self, name):
        command = 'createNetwork'

        params = {}
        params['name'] = name
        params['displaytext'] = name
        params['networkofferingid'] = self.networkofferingID 
        params['zoneid'] = self.zoneID 

        response = self.execAPICall(command, params)
        return response

    def listNetworkOfferings(self, name = None):
        command = 'listNetworkOfferings'
        params = {}
        if name:
            params['name'] = name

        params['SupportedServices'] = 'SourceNat' #FIXME
        params['state'] = 'enabled' #FIXME
        params['forVpc'] = 'false' #FIXME
        response = self.execAPICall(command, params)

        return response


    def listNetworks(self):
        command = 'listNetworks'
        response = self.execAPICall(command)
        return response


    def listZones(self):
        command = 'listZones'
        response = self.execAPICall(command)
        return response


    def getZoneID(self ):
        self.zoneID = None
        response = self.listZones()
        if not response:
           print "error: no zones found "
           return
        count = response['count']
        if count > 1:
            "WARNING: have multiple zones, using first returned"

        d = response['zone'][0]
        self.zoneName = d['name']
        self.zoneID = d['id']

        return self.zoneID


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
        try:
            response = self.execAPICall(command, params)
            return response
        except urllib2.HTTPError:
            logging.error("Problem querying for virtual machines")
            return None

    def listVirtualClusters(self, name = None):
        vms = {}
        response = self.listVirtualMachines(name)
        count = response['count']
        for i in range(count):
            d = response['virtualmachine'][i]
            vms[d['name']] =  d['state']

        # find longest VM name
        names = vms.keys()
        names.sort(key = len)
        for n in names:
            if self.vmNameSuffix in n:
               break
            len_fe = len(n)
        len_fe = max(len('frontend'), len_fe)
        len_compute = max(len('compute nodes'), len(names[-1]))

        # find longest VM status
        status = vms.values()
        status.sort(key = len)
        len_status = max(len('status'), len(status[-1]))

        lineformat = "%%-%ds  %%-%ds  %%-%ds  " % (len_fe,len_compute,len_status)

        vc = []

        if name: # list only one cluster 
            fe = None
            for k in sorted(vms.keys()):
                if name in k:
                    if fe:  # adding compute node info
                        vc.append(lineformat % (":", k, vms[k]))
                    else:  # adding frontend
                        fe = k 
                        vc.append(lineformat % (k, '-'*len_compute, vms[k]))

        else: # list all clusters
            fe = None
            for k in sorted(vms.keys()):
                if fe: 
                    if fe in k: # add compute node
                        vc.append(lineformat % (":", k, vms[k]))
                    else: # add  next frontend
                        fe = k
                        vc.append(lineformat % (k, '-'*len_compute, vms[k]))
                else: # add  first frontend
                    fe = k 
                    vc.append(lineformat % (k, '-'*len_compute, vms[k]))

        return vc


    def listServiceOfferings(self):
        command = 'listServiceOfferings'
        response = self.execAPICall(command)
        return response

    def getVirtualMachineIPs(self):
        """
        Returns a list of IPs for the existing Virtual Machine instances

        :return:  list of IPs 
        """

        ips = []

        response = self.listVirtualMachines()
        # check for errors
        if response is None:
           return ips
        # check for empty list of machines
        if "count" not in response:
            return ips

        count = response['count']
        for i in range(count):
            d = response['virtualmachine'][i]
            numnics = len(d['nic'])
            for n in range(numnics):
                nic = d['nic'][n]
                ips.append(nic['ipaddress'])
        return ips

    def getVirtualMachineID(self, name):
        """
        Returns an ID for the Virtual Machine instance
        :param name: Virtual Machine name 

        :return:  id (str) or None if no VM with this name was found
        """
        id = None
        response = self.listVirtualMachines(name)
        if not response:
           logging.error("No no Virtual Machine %s found" % name)
           return id

        count = response['count']
        for i in range(count):
            d = response['virtualmachine'][i]
            if d['name'] == name:
                id = d['id']
                break

        return id


    def getNetworkOfferingsID(self, name = None):
        response = self.listNetworkOfferings(name)
        if not response:
           print "error: no Network Offering name  %s found" % name
           return None

        count = len(response['networkoffering'])
        if count > 1:
            #FIXME. Should not get here. Need more logic
            print "Check for multiple network offerings."

        offering = response['networkoffering'][0]
        id = offering['id']

        return id


    def getTemplateID(self, name):
        id = None
        res = self.listTemplates(name)
        if not res:
           print "error: no template found"

        id = res['template'][0]['id']

        return id


    def getServiceOfferingID(self, ncpu, largest = False):
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
        largest_service = [-1, '']
        for i in alls:
            if i[0] > largest_service[0]:
                largest_service = i
            if i[0] < ncpu:
                continue
            else:
                id = i[1]
                break
        if largest and ncpu > largest_service[0]:
            return largest_service[1]
        else:
            return id


    def getFreeIP(self):
        """
        Find IPs of the existing Virtual Machines
        and return a tuple of next free IP address (str) 
        and its last octet (int)
        :return : a tuple (IP, octet)
        """
        
        octets = []
        subnet = None
        ips = self.getVirtualMachineIPs()
        if not ips :
            ips = self.getGatewayIPs()

        for i in ips:
            # answer contains [ first-3-octets, last-octet]
            answer = i.rsplit('.', 1)
            octets.append(int(answer[1]))
            subnet = answer[0]
        octets.sort()

        if not octets:
            logging.error("No IP information available from Cloudstack")
            return (None, None)

        #FIXME check for ip range
        lastoctet = 255
        octet = octets[0]
        while (octet in octets):
            octet = octet + 1
        if octet >= lastoctet:
            logging.error("No IPs available")
            return (None, None)
        
        ipaddress = "%s.%d" % (subnet, octet)

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

        # find IP for frontend 
        ip, octet = self.getFreeIP()
        if not ip:
            print "No free IP is available"
            return allocation

        # allocate cluster private network
        networks = {}
        response = self.listNetworks()

        count = response['count']
        for i in range(count):
            d = response['network'][i]
            networks[d['name']] =  d['id'] 

        privateNet = self.privateNetworkName + '%d' % octet
        if privateNet not in networks.keys():
            newnet = self.createNetwork(privateNet)
            networks[privateNet] = newnet['network']['id']
            
        publicNet = self.publicNetworkName
        if publicNet not in networks.keys():
            newnet = self.createNetwork(publicNet)
            networks[privateNet] = newnet['network']['id']

        ids = "%s,%s" % (networks[privateNet], networks[publicNet])

        # allocate frontend VM
        name = "%s%d" % (self.vmNamePrefix, octet)
        res = self.allocateVirtualMachine(fecpu, feTmpl, name, ip, ids)
        allocation.append(res)

        # allocate compute nodes 
        ids = "%s" % networks[privateNet]
        for i in range(num):
            name = "%s%d%s%d" % (self.vmNamePrefix, octet, self.vmNameSuffix, i)
            print "name", name
            res = self.allocateVirtualMachine(ccpu, computeTmpl, name, ip = None, ids = ids)
            allocation.append(res)

        return allocation


    def allocateVirtualMachine(self, ncpu, templatename, name, ip = None, ids = None, largest = False):
        command = 'deployVirtualMachine'

        # find required parameters for API call
        error = 0
        soid = self.getServiceOfferingID(ncpu, largest)
        if soid is None:
            print "Insufficient resources: service offering does not match request"
            error = 1
        tid = self.getTemplateID(templatename)
        if tid is None:
            print "Template for virtual machine %s not found" % templatename
            error = 1
        if error:
           print "Unable to allocate virtual machine from template %s" % templatename

        # XXX FIXME
        params = {}
        params['name'] = name
        params['serviceofferingid'] = soid
        params['templateid'] = tid
        params['zoneid'] = self.zoneID
        params['startvm'] = 'false'
        if ids:
            params['networkids'] = ids

        if ip:
            params['ipaddress'] = ip

        for p in params.keys():
            print "DEBUG", p, params[p]
        response = self.execAPICall(command, params)

        return response

    def deployVirtualMachine(self, ncpu, name):
        pass
        
    def stopVirtualMachine(self, id):
        """ 
        Stop virtual machine given its id
        :param id: Virtual Machine id 
        :return : an API call response as a dictionary 
        """ 
        command = 'stopVirtualMachine'

        params = {}
        params['id'] = id
        response = self.execAPICall(command, params)

        return response

    def startVirtualMachine(self, id):
        """ 
        Start virtual machine given its id
        :param id: Virtual Machine id 
        :return : an API call response as a dictionary 
        """ 
        command = 'startVirtualMachine'

        params = {}
        params['id'] = id
        response = self.execAPICall(command, params)

        return response


    def startVirtualCluster(self,name):
        """ 
        Start virtual cluster given its name
        :param name: Virtual Cluster name 
        :return : an API call response as a dictionary with 1 item
                  key = name, value = jobid (for start call) 
        """ 
        started = {}

        response = self.listVirtualMachines(name)
        count = response['count']
        for i in range(count):
            d = response['virtualmachine'][i]
            vmname = d['name']
            vmid = d['id']
            print "DEBUG starting", vmname, vmid
            vmresponse = self.startVirtualMachine(vmid)
            print "DEBUG keys", vmresponse.keys()
            started[vmname] = vmresponse['jobid']

        return started

    def stopVirtualCluster(self,name):
        """ 
        Stop virtual cluster given its name
        :param name: Virtual Cluster name 
        :return : an API call response as a dictionary with 1 item
                  key = name, value = jobid (for stop call) 
        """ 
        stopped = {}

        response = self.listVirtualMachines(name)
        count = response['count']
        for i in range(count):
            d = response['virtualmachine'][i]
            vmname = d['name']
            vmid = d['id']
            vmresponse = self.stopVirtualMachine(vmid)
            stopped[vmname] = vmresponse['jobid']

        return stopped

    def updateVirtualMachine(self, name, userdata):
        id = self.getVirtualMachineID(name)
        if not id:
            logging.error("Unable to add userdata to a VM %s" % name)
            return None

        params = {
            "userdata": base64.encodestring(userdata),
            "id": id
        }
        try:
            response = self.execAPICall("updateVirtualMachine", params)
        except urllib2.HTTPError as e:
            logging.error("Unable to allocate frontend: %s" % self.getError(e))
            return None

        return response
