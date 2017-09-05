#!/usr/bin/env python

import logging
import subprocess
import os
import re
import shlex
import xml.sax
from xml.sax import handler
from datetime import datetime
from subprocess import PIPE, Popen

import syslog

logger = logging.getLogger('pragma.util')
IP_ADDRESS_LEN = 15

def Abort(message, doExit=1):
        """Print a standard error message and throw a CommandError"""

        syslog.syslog(syslog.LOG_ERR, message)
        raise CommandError(message)


def get_id():
    return "%i-%s" % (os.getpid(), datetime.now().strftime("%Y-%m-%d"))

def getRocksOutputAsList(cmdline, inputString=None):
    return getOutputAsList("/opt/rocks/bin/rocks %s" % cmdline, inputString)


def getOutput(cmdline, inputString=None):
	""" run popen pipe inputString and return a touple of
  (the stdout as a list of string, return value of the command)
  """
	logger.debug("Executing command: '%s'" % cmdline)
	if isinstance(cmdline, unicode):
		cmdline = str(cmdline)
	if isinstance(cmdline, str):
		# needs to make a list
		cmdline = shlex.split(cmdline)
	p = Popen(cmdline, stdin=PIPE, stdout=PIPE, stderr=subprocess.STDOUT)
	grep_stdout = p.communicate(input=inputString)[0]
	p.wait()
	return (grep_stdout, p.returncode)

def getOutputAsList(cmdline, inputString=None):
	(grep_stdout, returncode) = getOutput(cmdline, inputString)
	return (grep_stdout.split('\n'), returncode)

def getPatterns(pattern, astring):
  pattern_c = re.compile(pattern)
  result = pattern_c.search(astring)
  if result:
    return result.groups()
  else:
    return []

# copied from stackoverflow
# http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python/377028
def which(program):

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


def any(iterable):
    for element in iterable:
        if element:
            return True
    return False

def all(iterable):
    for element in iterable:
        if not element:
            return False
    return True


# Pragma exception hierarchy, copied from Rocks
class PragmaException(Exception):
	"""Base class for Pragma exceptions."""
	pass

class HostnotfoundException(PragmaException):
	"""This exception is used when the given host does not exist"""
	pass

class ParameterNotValid(PragmaException):
	"""This exception is used when the user input parameters are 
	not valid"""
	pass

class CommandError(PragmaException):
	"""This exception is thrown by the command line when 
	something goes awry"""
	pass


class Struct:
    pass


def escapeAttr(value):
	"""escape attribute values with XML escaping"""
	return xml.sax.saxutils.escape(value, { "\"": "&quot;",
						"%": "&#x0025;",
						"'": "\\'"})

def unescapeAttr(value):
	"""unescape attribute values with XML escaping """
	return xml.sax.saxutils.unescape(value, {"&quot;": "\"",
						"&#x0025;": "%"})

def escapeStringForShell(string):
	"""escape the given string so that it can be used in a shell script
	inside a double quote string"""
	return string.replace("\"", "\\\"") 

def str2bool(s):
	"""Converts an on/off, yes/no, true/false string to 1/0."""
	if s and s.upper() in [ 'ON', 'YES', 'Y', 'TRUE', '1', 'ENABLED', 'ENABLE']:
		return True
	else:
		return False

def bool2str(b):
	"""Converts an 1/0 to a yes/no"""
	if b:
		return 'yes'
	else:
		return 'no'

def list2str(list):
    s = ''
    for e in list:
        s = s + e
    return s


def listcmp(l1, l2):
    return map(lambda a,b: a==b, l1, l2)

def listdup(e, n):
    l = []
    for i in range(0, n):
        l.append(e)
    return l


def list_isprefix(l1, l2):
    l = listcmp(l1, l2)
    for i in range(0, len(l1)):
        if not l[i]:
            return 0
    return 1
        


def getNativeArch():
	"""Returns the canotical arch as reported by the operating system"""
	
	arch = os.uname()[4]
	if arch in [ 'i386', 'i486', 'i586', 'i686']:
		arch = 'i386'
	return arch

 
def mkdir(newdir):
	"""Works the way a good mkdir should :)
		- already exists, silently complete
		- regular file in the way, raise an exception
		- parent directory(ies) does not exist, make them as well
		From Trent Mick's post to ASPN."""
	if os.path.isdir(newdir):
		pass
	elif os.path.isfile(newdir):
		raise OSError("a file with the same name as the desired " \
					"dir, '%s', already exists." % newdir)
	else:
		head, tail = os.path.split(newdir)
		if head and not os.path.isdir(head):
			mkdir(head)
		if tail:
			os.mkdir(newdir)



class ParseXML(handler.ContentHandler,
		  handler.DTDHandler,
		  handler.EntityResolver,
		  handler.ErrorHandler):
	"""A helper class to for XML parsers. Uses our
	startElement_name style."""

	def __init__(self, app=None):
		handler.ContentHandler.__init__(self)
		self.app = app
		self.text = ''
		

	def startElement(self, name, attrs):
		"""The Mason Katz school of parsers. Make small functions
		instead of monolithic case statements. Easier to override and
		to add new tag handlers."""
		try:
			f = getattr(self, "startElement_%s" % name)
			f(name, attrs)
		except AttributeError:
			return


	def endElement(self, name):
		try:
			f = getattr(self, "endElement_%s" % name)
			f(name)
		except AttributeError:
			return


	def characters(self, s):
		self.text += s


def system(cmd, type='standard'):
	if type == 'spinner':
		return startSpinner(cmd)
	else:
		return subprocess.call(cmd, shell=True)

		

def startSpinner(cmd):
	"""This used to just be a system() but now we
	control the child output to keep the status
	on one line using stupid CR terminal tricks.
	We even add a way cool spinny thing in
	column zero just to be l33t!
	
	Does not show standard error output."""

	p = subprocess.Popen(cmd, shell=True, 
          	stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
		stderr=subprocess.PIPE, close_fds=True)
	w, r ,e = (p.stdin, p.stdout, p.stderr)
	currLength  = 0
	prevLength  = 0
	spinChars   = '-\|/'
	spinIndex   = 0
	while 1:
		line = e.readline()
		if not line:
			break
		if len(line) > 79:
			data = line[0:78]
		else:
			data = line[:-1]
		currLength = len(data)
		pad = ''
		for i in range(0, prevLength - currLength):
			pad = pad + ' '
		spin  = spinChars[spinIndex % len(spinChars)]
		spinIndex = spinIndex + 1
		print spin + data + pad + '\r',
		prevLength = currLength
		sys.stdout.flush()
	r.close()
	w.close()
	e.close()
		
	# Cleanup screen when done
		
	pad = ''
	for i in range(0,78):
		pad = pad + ' '
	print '\r%s\r' % pad,
	
def getListHeader(strings):
	# initialize 
	len_fe = 0
	len_compute = 0
	len_status = 0

	# find max string length for frontend, compute node and status
	for str in strings:
		items = str.split()
		len_fe = max(len(items[0]), len_fe)
		len_compute = max(len(items[1]), len_compute)
		len_status = max(len(items[2]), len_status)

	len_fe = max(len('FRONTEND'), len_fe)
	len_compute = max(len('COMPUTE NODES'), len_compute)
	len_status = max(len('STATUS'), len_status)

        lineformat = "%%-%ds  %%-%ds  %%-%ds  %%-%ds" % (len_fe,len_compute,len_status, IP_ADDRESS_LEN)

	return lineformat % ('FRONTEND', 'COMPUTE NODES', 'STATUS', 'PUBLIC IP')


class Iface:
	def __init__(self, ip, mac, iface):
		self.ip = ip
		self.iface = iface
		self.mac = mac

	def __str__(self):
		return "%s, %s, %s" % (self.ip, self.iface, self.mac)

	def get_attrs(self):
		return {'ip': self.ip, 'mac': self.mac, 'iface': self.iface}


class Network:
	def __init__(self, subnet, netmask, mtu):
		self.subnet = subnet
		self.subnet_pat = self.subnet.replace(".0", ".%d")
		self.netmask = netmask
		self.counter = [255]*self.subnet.count(".0")
		self.frontend = [1]*self.subnet.count(".0")
		self.mtu = mtu

	def __str__(self):
		return '%s, %s, %s' % (self.subnet, self.netmask, self.mtu)

	def get_free_ip(self):
		for idx, count in enumerate(self.counter):
			if count > 1:
				self.counter[idx] -= 1
				break
			elif idx == len(self.counter)-1:
				raise OverflowError("No free IP addresses left")
			else:
				self.counter[idx] = 254

		return self.subnet_pat % tuple(self.counter[::-1])

	def get_frontend_ip(self):
		return self.subnet_pat % tuple(self.frontend)

	def get_attrs(self):
		return {'netmask': self.netmask, 'subnet': self.subnet, 'mtu': self.mtu}


class Node:
	def __init__(self, name):
		self.ifaces = {}
		self.gw = None
		self.name = name

	def __str__(self):
		ifaces = []
		for name, iface in self.ifaces.items():
			ifaces.append("%s (%s)" % (name, str(iface)))
		return "%s\n%s" % (self.gw, ", ".join(ifaces))

	def add_gw(self, gw):
		self.gw = gw

	def add_iface(self, name, ip, mac, iface):
		self.ifaces[name] = Iface(ip, mac, iface)

	def get_gw(self):
		return self.gw

	def get_ifaces(self):
		return self.ifaces

	def get_name(self):
		return self.name


class ClusterNetwork:
	def __init__(self, frontend, fqdn):
		self.nodes = {}
		self.nets = {}
		self.frontend = frontend
		self.fqdn = fqdn
		self.counter = 0
		self.computes = []

	def __str__(self):
		networks = "Networks:\n"
		for name, net in self.nets.items():
			networks += "%s: %s\n" % (name, str(net))
		nodes = "Nodes:\n"
		for name, node in self.nodes.items():
			nodes += "%s: %s\n" % (name, str(node))
		return "Name: %s\nFqdn: %s\n%s\n%s" % (
			self.frontend, self.fqdn, nodes, networks)

	def add_gw(self, node, gw):
		self.nodes[node].add_gw(gw)

	def add_net(self, name, subnet, netmask, mtu):
		if name not in self.nets:
			self.nets[name] = Network(subnet, netmask, mtu)

	def add_iface(self, node, net, ip, mac, iface):
		if node not in self.nodes:
			if node == self.frontend:
				self.nodes[node] = Node(self.frontend)
			else:
				self.computes.append(node)
				self.nodes[node] = Node('compute-%i' % self.counter)
				self.counter += 1
		if re.search("[\-]+", net) is not None:
			net = 'private'
		if re.search("[\-]+", ip) is not None:
			ip = self.nets[net].get_free_ip()
		self.nodes[node].add_iface(net, ip, mac, iface)

	def get_computes(self):
		return self.computes

	def get_frontend(self):
		return self.frontend

	def get_frontend_ip(self, net):
		return self.nets[net].get_frontend_ip()

	def get_fqdn(self):
		return self.fqdn

	def get_gw(self, node):
		return self.nodes[node].get_gw()

	def get_ifaces(self, node):
		if node == 'frontend':
			node = self.frontend
		return self.nodes[node].get_ifaces()

	def get_net_attrs(self, net):
		return self.nets[net].get_attrs()

	def get_node_name(self, node):
		return self.nodes[node].get_name()



