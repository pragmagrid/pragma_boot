#!/usr/bin/env python

import hashlib
import hmac
import base64
import json
import urllib2
import urllib

class CloudStackCall():

    def __init__(self, url, key, secret):
        self.apiUrl = url
        self.apiKey = key
        self.apiSecret = secret
        self.json = 'json'
        self.request = {}

        self.templatefilter = 'community'

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
        wrapped_response_dict = json.loads(response_str)

        # TODO check for errors
        return  wrapped_response_dict[self.request['command'].lower() + 'response']

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

    def listTemplates(self, name = None):
        command = 'listTemplates'
        params = {}
        params['templatefilter'] = self.templatefilter
        if name:
            params['name'] = name
        response = self.execAPICall(command, params)

        return response


    def listVirtualMachines(self, name = None):
        command = 'listVirtualMachines'
        params = {}
        if name:
            params['name'] = name
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

    def getVirtualMachineIPs(self):
        """
        Returns a list of IPs for the Virtual Machine instances

        :return:  list of IPs 
        """
        response = self.listVirtualMachines()
        if not response:
           print "error: no Virtual Machine found" 
           return
        ips = []
        count = response['count']
        for i in range(count):
            d = response['virtualmachine'][i]
            #XXXprint "D", d
            nic = d['nic'][0]
            ips.append(nic['ipaddress'])
            #XXXprint nic['networkname']
        print "IPs: ", ips
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
            #XXX print "id", d['id']
            if d['name'] == name:
                ids.append(d['id'])

        return ids


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


    def allocateVirtualMachine(self, ncpu, name):
        command = 'deployVirtualMachine'

        # find required parameters for API call
        error = 0
        soid = self.getServiceOfferingID(ncpu)
        if soid is None:
            print "Insufficient resources: service offering does not match request"
            error = 1
        tid, zid = self.getTemplateZoneIds(name)
        if tid  is None or zid is None:
            print "Template for virtual machine %s not found" % name
            error = 1
        if error:
           print "Unable to allocate virtual machine from template %s" % name

        params = {}
        params['serviceofferingid'] = soid
        params['templateid'] = tid
        params['zoneid'] = zid
        params['startvm'] = 'false'

        octets = []
        ips = self.getVirtualMachineIPs()

        response = self.execAPICall(command, params)
        print response
#{u'id': u'3fc35908-7d76-4bf8-a28e-ea3bf568fdea', u'jobid': u'fc398295-02b9-4d91-bfd6-22c8479d5047'}

        return

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

