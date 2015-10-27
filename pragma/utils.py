#! /opt/rocks/bin/python

from subprocess import PIPE, Popen
import subprocess
import os
import shlex
import xml.sax
from xml.sax import handler

global BASEPATH

def getOutputAsList(cmdline, inputString=None):
    """ run popen pipe inputString and return a touple of
    (the stdout as a list of string, return value of the command)
    """
    if isinstance(cmdline, unicode):
        cmdline = str(cmdline)
    if isinstance(cmdline, str):
        # needs to make a list
        cmdline = shlex.split(cmdline)
    p = Popen(cmdline, stdin=PIPE, stdout=PIPE, stderr=subprocess.STDOUT)
    grep_stdout = p.communicate(input=inputString)[0]
    p.wait()
    return (grep_stdout.split('\n'), p.returncode)



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

def getRepository():
	"""Returns repository object based on site_conf.conf file"""

	# Read in site configuration file and imports values:
	#   site_ve_driver, temp_directory,
	#   repository_class, repository_dir, repository_settings
	conf_path = os.path.join(BASEPATH, "etc", "site_conf.conf")
	if not(os.path.exists(conf_path)):
		self.abort('Unable to find conf file: ' + conf_path)
	execfile(conf_path, {}, globals())

	fullpath = repository_class.split(".")
	from_module = ".".join(fullpath[:-1])
	classname = fullpath[-1]
	module = __import__(from_module, fromlist=[classname])
        klass = getattr(module, classname)

	repository_settings["cache_dir"] = repository_dir
	repository = klass(repository_settings)

	return repository
 
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
	

