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

    def listTemplates(self):
        comm = {}
        comm['command'] = 'listTemplates'
        comm['templatefilter'] = 'community'
        self.buildRequest(comm)
        response_dict = self.sendRequest()
        #print "list templates ", response_dict

    def listVirtualMachines(self):
        comm = {}
        comm['command'] = 'listVirtualMachines'
        self.buildRequest(comm)
        response_dict = self.sendRequest()
        #print "D", response_dict
        count = response_dict['count']
        for i in range(count):
            d = response_dict['virtualmachine'][i]
            print "id", d['id']

    def stopVirtualMachine(self):
        """ place holder for now """
        pass
        # for stopVirtualMachine returns 
        #C {u'jobid': u'0020f91e-5854-4ce7-94dd-4b5b3cf7909d'}

# Main 
apikey = 'nWcPrqXC60UAfHyRqXsqm-JZPTHiCIQmMGO0eSp5_GyO9-0p51qC05a7xpgvtVAC1CM-yK4rGB_ROFVYn912HA'
secretkey = 'Y5kSgRBn70NpGRSlmeL9ea6lkZj1fn77VRZKZxz0GkXjrwl86fW72mY5OxE2SAlqX3sudIVe1ZYyVm969dAUww'
baseurl='http://163.220.56.65:8080/client/api?'

apicall = CloudStackCall(baseurl, apikey, secretkey)
apicall.listTemplates()
apicall.listVirtualMachines()

