#!/usr/bin/env python

import hashlib
import hmac
import base64
import json
import re
import sys
import time
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
        self.defaultPorts = ['22', '443', '80']
        self.defaultProto = ['tcp', 'udp', 'icmp']
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
        sig_str = '&'.join(['='.join([k.lower(),urllib.quote_plus(self.request[k], safe="*").lower().replace('+','%20').replace("%3A", ":")])
                   for k in sorted(self.request.iterkeys())])
        self.sig = urllib.quote_plus(base64.b64encode(hmac.new(self.apiSecret, sig_str, hashlib.sha1).digest()).strip())

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

    def createEgressFirewallRule(self, network_id, protocol, cidrlist = '0.0.0.0/0'):
        """ 
	Open network firewall to specified protocol and cidr list.  This is a
        blocking call.

        :param network_id: The id of the network to open
        :param protocol: Name of protocol (tcp, udp, or icmp)
        :param cidrlist: Allowed source IP addresses in CIDR notation

        :return : an API call response as a dictionary 
        """ 
        command = 'createEgressFirewallRule'

        params = {}
        params['networkid'] = id
        params['protocol'] = protocol
        params['cidrlist'] = cidrlist

        return self.execAPICallAndWait(command, params)
        print response

    def createNetwork(self, name):
        """ 
	Create a new network in default zone.  

        :param name: The name to give the new network
        :return : an API call response as a dictionary 
        """ 
        command = 'createNetwork'

        params = self.getFreeNetwork()
        params['name'] = name
        params['displaytext'] = name
        params['networkofferingid'] = self.networkofferingID 
        params['zoneid'] = self.zoneID 

        return self.execAPICall(command, params)

    def openNetwork(self, network_id, protos=None):
        """ 
        Open up the firewall to the specified protocols (e.g., tcp)

        :param network_id: The id of the network to open
        :param protos: Optional list of specific protocols

        :return : True if successful, otherwise False
        """ 
        if protos is None:
            protos = self.defaultProto
        for proto in protos:
            firewall_response = self.createEgressFirewallRule(network_id, proto)
            if 'firewallrule' not in firewall_response:
                logging.error("Problem setting egress firewall rule for %s" % proto)
                return False

        return True

    def deleteNetwork(self, id):
        """ 
        Delete network 
        :param id: The id of the network to delete
        :return : an API call response as a dictionary with 1 item
                  key = id, value = jobid (for delete call) 
        """ 
        command = 'deleteNetwork'

        params = {}
        params['id'] = id

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

    def getNetwork(self, name):
        """ 
        Get the network object information for specific network
        :param name: The name of the network 
        :return : an object containing key value pairs
        """ 
        res = self.listNetworks()
        for network in res["network"]:
            if network["name"] == name:
                return network
        return None

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
        vms = {}  # dictionary of available VMS {name: state}
        vc = []   # return value, list of virtual clusters with the status 

        # virtual machine  name is not found
        response = self.listVirtualMachines(name)
        if response is None:
            self.clusterNotFound(name)
            return vc
        if len(response) < 1:
          return vc
        
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

    def getVirtualMachineIPs(self, id = None):
        """
        Returns a list of public IPs for the existing Virtual Machine instances

        :return:  list of public IPs 
        """

        ips = []

        response = self.listVirtualMachines(id)
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
                if nic['networkname'] == self.publicNetworkName:
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
           logging.error(" No virtual host %s found" % name)
           return id

        count = response['count']
        for i in range(count):
            d = response['virtualmachine'][i]
            if d['name'] == name:
                id = d['id']
                break

        return id

    def getVirtualMachinePrivateNetwork(self, name):
        """ 
        Get the private network name of a virtual machine
        :param name: virtual machine  name 
        :return : a string containing the name of the private network
        """ 
        response = self.listVirtualMachines(name)
        networks = {}
        for vm in response['virtualmachine']:
            if vm['name'] == name:
                for nic in vm['nic']:
                    if nic["networkname"] != self.publicNetworkName:
                        return nic["networkname"]


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

    def getFreeNetwork(self):
        """ 
	Get an unused private network space.  This is a simple algorithm that
	will allocate 10.xx.xx.0/24 spaces.  Cloudstack will not allow anything
        bigger than 24.

	:return : New network information as a dictionary with keys startip,
                  endip, gateway, and netmask
        """ 
        networks = self.listNetworks()
        for i in range(3, 255):
            for j in range(3, 255):
                candidateNetwork = "10.%d.%d.0/24" % (i,j)
                found = False
                if networks:
                    for net in networks['network']:
                        if net['cidr'] == candidateNetwork:
                            found = True
                if not found:
                    return { 'startip': '10.%d.%d.2' % (i,j),
                             'endip': '10.%d.%d.255' % (i,j),
                             'gateway': '10.%d.%d.1' % (i,j),
                             'netmask': '255.255.255.0' }

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
            ips = self.getGatewayIPs(self.publicNetworkName)

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

    def getGatewayIPs(self, name = None):
        """ 
	Return the gateway IPs for all network or just the specific network 

        :param name:  Name of network to return gateway IP address

        :return : an array containing the IP addresses as strings
        """ 
        ips = []
        response = self.listNetworks()
        if not response:
            return ips
        count = response['count']
        for i in range(count):
            d = response['network'][i]
            gatewayIP = d['gateway']
            if name is not None and d['name'] != name:
                continue
            if gatewayIP not in ips:
                ips.append(d['gateway'])

        return ips

    def allocateVirtualCluster(self, feTmpl, fecpu, computeTmpl, cpus):
        """
        Allocate Virtual cluster

        :param feTmpl: template for frontend 
        :param fecpu: number of cpus for FE
        :param computeTmpl: template for compute 
        :param ccpu: number of cpus per compute node
        :param num: number of compute nodes
        """

        allocation = []

        # allocate cluster public network if it doesn't exist
        networks = {}
        response = self.listNetworks()

        count = response['count']
        for i in range(count):
            d = response['network'][i]
            networks[d['name']] =  d['id'] 

        publicNet = self.publicNetworkName
        if publicNet not in networks.keys():
            newnet = self.createNetwork(publicNet)
            if not self.openNetwork(newnet['network']['id']):
                logging.error("Unable to open public network")
            networks[publicNet] = newnet['network']['id']

        response = self.associateIpAddress(networks[publicNet])
        if 'ipaddress' not in response and 'id' not in response['ipaddress']:
            logging.error("Unable to acquire public IP address")
            return []
        publicip_id = response['ipaddress']['id']
        logging.info("Acquired public IP address %s" % response['ipaddress']['ipaddress'])
        for port in self.defaultPorts:
            firewall_obj = self.createFirewallRule(publicip_id, 'tcp', port)
            if 'firewallrule' not in firewall_obj:
                logging.error("Unable to open firewall on IP address for port %s" % port)
                return []

        # allocate cluster private network
        # find IP for frontend 
        ip, octet = self.getFreeIP()
        if not ip:
            print "No free IP is available"
            return allocation

        privateNet = self.privateNetworkName + '%d' % octet
        if privateNet not in networks.keys():
            newnet = self.createNetwork(privateNet)
            networks[privateNet] = newnet['network']['id']
            
        # allocate frontend VM
        name = "%s%d" % (self.vmNamePrefix, octet)
        res = self.allocateVirtualMachine(fecpu, feTmpl, name, networks[privateNet], networks[publicNet], ip)
        
        fe_id = res["virtualmachine"]['id']
        for port in self.defaultPorts:
            portforward_obj = self.createPortForwardingRule(publicip_id, 'tcp', port, fe_id)
            if 'portforwardingrule' not in portforward_obj:
                logging.error("Unable to forward port %s from public IP to VM" % port)
                return []
        allocation.append(res)

        # allocate compute nodes 
        ids = "%s" % networks[privateNet]
        i = 0
        while(cpus > 0):
            name = "%s%d%s%d" % (self.vmNamePrefix, octet, self.vmNameSuffix, i)
            res = self.allocateVirtualMachine(cpus, computeTmpl, name, networks[privateNet], None, None, True)
            allocation.append(res)
            cpus_used = res["virtualmachine"]["cpunumber"]
            cpus -= cpus_used
            i += 1

        return allocation

    def execAPICallAndWait(self, command, params):
        """ 
	Execute the specified asynchronous Cloudstack call and wait for the
        result

        :param command:  Name of Cloudstack REST API call
	:param params:  Dictionary containing the Cloudstack command args 

	:return : A dictionary containing the response from Cloudstack or None
                  if error
        """ 
        job = None
        try:
            job = self.execAPICall(command, params)
        except urllib2.HTTPError as e:
            logging.error("Problem sending Cloudstack command %s: %s" % command)
            return None
        jobresults = self.waitForAsyncJobResults([job['jobid']])
        if 'jobresult' not in jobresults[job['jobid']]:
            logging.error("'jobresult' not found in response: %s" % str(jobresults))
            return None
        return jobresults[job['jobid']]['jobresult']

    def createPortForwardingRule(self, ip_id, protocol, port, vm_id):
        """ 
	Forward traffic from Cloudstack public IP port to VM private IP port

        :param ip_id:  Cloudstack identifier for public IP
	:param protocol:  Protocol of traffic to forward
	:param port:  Port of traffic to forward
        :param vm_id:  Cloudstack identifier for virtual machine

	:return : A dictionary containing the response from Cloudstack or None
                  if error
        """ 
        command = 'createPortForwardingRule'

        params = {}
        params['ipaddressid'] = ip_id
        params['protocol'] = protocol
        params['publicport'] = port
        params['privateport'] = port
        params['virtualmachineid'] = vm_id

        return self.execAPICallAndWait(command, params)

    def createFirewallRule(self, ip_id, protocol, port, cidrlist='0.0.0.0/0'):
        """ 
	Allow traffic to Cloudstack public IP port 

        :param ip_id:  Cloudstack identifier for public IP
	:param protocol:  Open traffic to protocol 
        :param port:  Port to open
        :param cidrlist: Allowed source IP addresses in CIDR notation

	:return : A dictionary containing the response from Cloudstack or None
                  if error
        """ 
        command = 'createFirewallRule'

        params = {}
        params['ipaddressid'] = ip_id
        params['protocol'] = protocol
        params['startport'] = port
        params['endport'] = port
        params['cidrlist'] = cidrlist 

        return self.execAPICallAndWait(command, params)

    def associateIpAddress(self, networkid):
        """ 
	Create a new public IP address for the specified network

        :param networkid:  Cloudstack identifier for network

	:return : A dictionary containing the response from Cloudstack or None
                  if error
        """ 
        command = 'associateIpAddress'

        params = {}
        params['networkid'] = networkid
        params['zoneid'] = self.zoneID

        return self.execAPICallAndWait(command, params)

    def allocateVirtualMachine(self, ncpu, templatename, name, private_id, public_id = None, ip = None, largest = False):
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
        params['iptonetworklist[0].networkid'] = private_id
        if public_id:
            params['iptonetworklist[1].networkid'] = public_id
            if ip: 
                params['iptonetworklist[1].ip'] = ip

        response = self.execAPICall(command, params)
        jobresults = self.waitForAsyncJobResults([response['jobid']])
        if 'jobresult' not in jobresults[response['jobid']]:
            return None
        return jobresults[response['jobid']]['jobresult']


    def deployVirtualMachine(self, ncpu, name):
        pass

    def destroyVirtualMachine(self, id):
        """ 
        Destroy virtual machine given its id
        :param id: Virtual Machine id 
        :return : an API call response as a dictionary 
        """ 
        command = 'destroyVirtualMachine'

        params = {}
        params['id'] = id
        response = self.execAPICall(command, params)

        return response

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

        try:
            response = self.execAPICall(command, params)
        except urllib2.HTTPError as e:
            logging.error("Unable to start vm %s: %s" % (name, self.getError(e)))
            return None
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
            vmresponse = self.startVirtualMachine(vmid)
            print "DEBUG keys", vmresponse.keys()
            started[vmname] = vmresponse['jobid']

        return started

    def clusterNotFound(self,name):
        print "Error: cannot resolve host \"%s\"" % name
        return

    def destroyVirtualCluster(self,name, max_attempts = 100):
        """ 
        Remove virtual cluster given its name
        :param name: Virtual Cluster name 
        :param max_attempts: Maximum attempts at deleting virtual cluster network
        :return : True if successful, otherwise False
        """ 

        # virtual cluster can only be destroyed if all VMs are stopped
        running = []
        response = self.listVirtualMachines(name)
        if not response: # cluster name not found
            self.clusterNotFound(name)
            return False
        for vm in response['virtualmachine']:
            if vm['state'] != "Stopped": 
                running.append(vm['name'])
        if len(running) > 0:
            print "\nError, unable to destroy virtual cluster"
            print "The following VMs are not in Stopped state: %s" % ", ".join(running)
            return False
        
        # get vc private network so we can destroy later
        privateNetwork = self.getVirtualMachinePrivateNetwork(name)

        # release public IP
        for vm in response['virtualmachine']:
            if vm['name'] == name: # frontend
                ip = self.listPublicIpAddresses(vm['id'])
                if ip is not None:
                    ip_response = self.disassociateIpAddress(ip['id'])
                    if 'success' in ip_response and ip_response['success']:
                        print
                        print "Released pubic IP address %s" % ip['ipaddress']
                        print

        # destroy VMs
        jobids = {}
        for vm in response['virtualmachine']:
            vmresponse = self.destroyVirtualMachine(vm['id'])
            jobids[vm['name']] = vmresponse['jobid']
        jobresults = self.waitForAsyncJobResults(jobids.values())
        destroyed = {}
        for vmname, jobid in jobids.items():
            if jobresults[jobid]['jobresultcode'] == 0:
                destroyed[vmname] = "Destroyed"
            else:
                destroyed[vmname] = str(jobresults[jobid]['jobresult'])
        
        # print vm status
        self.printVMStatusTable(destroyed)
        print

	# Now clean up private network -- does not delete until some server
	# state clears out so we just repeat call until it succeeds
	sys.stdout.write("Removing network %s (this may take 5 mins)..." % privateNetwork)
        vc_net = self.getNetwork(privateNetwork)
        for i in range(0,max_attempts):
            sys.stdout.write(".")
            sys.stdout.flush()
            job = self.deleteNetwork(vc_net["id"])
            jobresult = self.waitForAsyncJobResults([job["jobid"]])
            if jobresult[job["jobid"]]['jobresultcode'] == 0:
                print "success"
                return True
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(10)
        
        # else we were unsuccessful after max_attempts
        print "\nError, unable to delete network %s" % privateNetwork
        return False

    def disassociateIpAddress(self, ip_id):
        """ 
	Release public IP address 

        :param ip_id:  Cloudstack identifier for public IP address

	:return : A dictionary containing the response from Cloudstack or None
                  if error
        """ 
        command = 'disassociateIpAddress'

        params = {'id': ip_id}
        try:
            response = self.execAPICallAndWait(command, params)
        except urllib2.HTTPError as e:
            logging.error(self.getError(e))
            return None
        return response


    def listPublicIpAddresses(self, vmid=None):
        """ 
	List all public IP addresses or just for specified VM

        :param vmid:  Cloudstack identifier for virtual machine

	:return : A dictionary containing the response from Cloudstack or None
                  if error
        """ 
        command = 'listPublicIpAddresses'

        try:
            response = self.execAPICall(command, {})
        except urllib2.HTTPError as e:
            logging.error(self.getError(e))
            return None

        if 'publicipaddress' not in response:
            return None

        if vmid is None:
            return response

        for ip in response['publicipaddress']:
            rules = self.listPortForwardingRules(ip['id'])
            if 'count' not in rules:
                continue
            a_rule = rules['portforwardingrule'][0]
            if a_rule['virtualmachineid'] == vmid:
              return ip
        return None

    def listPortForwardingRules(self, ip_id):
        """ 
	List all port forwarding rules for the specified public IP 

        :param ip_id:  Cloudstack identifier for public IP

	:return : A dictionary containing the response from Cloudstack or None
                  if error
        """ 
        command = 'listPortForwardingRules'

        params = {'ipaddressid': ip_id}
        try:
            response = self.execAPICall(command, params)
        except urllib2.HTTPError as e:
            logging.error(self.getError(e))
            return None
        return response
    

    def stopVirtualCluster(self,name):
        """ 
        Stop virtual cluster given its name
        :param name: Virtual Cluster name 
        :return : an API call response as a dictionary with 1 item
                  key = name, value = jobid (for stop call) 
        """ 
        header = "HOST    STATUS"
        stopped = {}

        response = self.listVirtualMachines(name)
        if not response: # cluster name not found
            self.clusterNotFound(name)
            return 0

        count = response['count']
        jobids = {}
        for i in range(count):
            d = response['virtualmachine'][i]
            vmname = d['name']
            vmid = d['id']
            state = d['state']
            if state == "Stopped": 
                stopped[vmname] = "Already in stopped state"
            else:
                vmresponse = self.stopVirtualMachine(vmid)
                jobids[vmname] = vmresponse['jobid']

        if len(jobids) > 0:
            jobresults = self.waitForAsyncJobResults(jobids.values())
            for vmname, jobid in jobids.items():
                if jobresults[jobid]['jobresultcode'] == 0:
                    stopped[vmname] = "Stopped"
                else:
                    stopped[vmname] = str(jobresults[jobid]['jobresult'])

        if stopped: 
            self.printVMStatusTable(stopped)
            return 1
        else:
            print "nothing to stop"
            return 0

    def updateVirtualMachine(self, id, updates):
        updates["id"] = id
        try:
            response = self.execAPICall("updateVirtualMachine", updates)
        except urllib2.HTTPError as e:
            logging.error("Unable to update vm %s: %s" % (id,self.getError(e)))
            return None
        return response


    def queryAsyncJobResult(self, id):
        command = 'queryAsyncJobResult'

        params = {}
        params['jobid'] = id

        try:
            response = self.execAPICall(command, params)
        except urllib2.HTTPError as e:
            logging.error(self.getError(e))
            return None

        return response


    def listAsyncJobs(self):
        """ On success returns a dictionary { 'count': num, 'asyncjobs': [list]}
            Each item in a list is a dictionary. To get VM values use dict key 'jobresult' 
            which has a value as a dictionary {u'virtualmachine': {vm info here}
            Any command using listAsyncJobs() will need to process return values 
                count = response['count']
                for i in range(count):
                    r = response['asyncjobs'][i]
                    d = r['virtualmachine'][i]
                    vmname = d['name']
                    vmid = d['id']
                    ...
        """
        command = 'listAsyncJobs'

        response = self.execAPICall(command)
        return response

    def waitForAsyncJobResults(self, job_ids, checkperiod=10, max_attempts=100):
        """ Wait for jobstatus to go to nonzero (0 is pending)"""
        jobresults = {}
        for i in range(0, max_attempts):
            time.sleep(checkperiod)
            for job_id in job_ids:
                job = self.queryAsyncJobResult(job_id)
                if job['jobstatus'] != 0:
                    jobresults[job_id] = job
            if len(jobresults) ==  len(job_ids):
                return jobresults
        # otherwise we return the ones we have
        return jobresults


    def printVMStatusTable(self, status):
        names = status.keys()
        names.sort(key = len)
        len_name = max(len('HOST'), len(names[-1]))  # longest host name
        lineformat = "%%-%ds  %%-20s  " % (len_name) # format string

        print lineformat % ("HOST", "STATUS")
        for k in sorted(status.keys()):
            print  lineformat % (k, status[k])
