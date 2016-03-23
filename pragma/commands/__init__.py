import os
import socket
import string
import re
import syslog
import pwd
import types
import sys
import traceback

import pragma
import xml
from xml.sax import saxutils
from xml.sax import handler
from xml.sax import make_parser
from xml.sax._exceptions import SAXParseException


def Abort(message, doExit=1):
	"""Print a standard error message and throw a
	pragma.util.CommandError"""
	
	syslog.syslog(syslog.LOG_ERR, message)
	raise pragma.util.CommandError(message)


class OSArgumentProcessor:
	"""An Interface class to add the ability to process os arguments."""

	def getOSNames(self, args=None):
		"""Returns a list of OS names.  For each arg in the ARGS list
		normalize the name to one of either 'linux' or 'sunos' as
		they are the only supported OSes.  If the ARGS list is empty
		return a list of all supported OS names.
		"""

		list = []
		for arg in args:
			s = arg.lower()
			if s == 'linux':
				list.append(s)
			elif s == 'sunos':
				list.append(s)
			else:
				self.abort('unknown os "%s"' % arg)
		if not list:
			list.append('linux')
			list.append('sunos')

		return list
	

		
class DocStringHandler(handler.ContentHandler,
	handler.DTDHandler,
	handler.EntityResolver,
	handler.ErrorHandler):
	
	def __init__(self, name='', users=[]):
		handler.ContentHandler.__init__(self)
		self.text			= ''
		self.name			= name
		self.users			= users
		self.section			= {}
		self.section['description']	= ''
		self.section['arg']		= []
		self.section['param']		= []
		self.section['example']		= []
		self.section['related']		= []
		self.parser = make_parser()
		self.parser.setContentHandler(self)

	def getDocbookText(self):
		s  = ''
		s += '<section id="rocks-%s" xreflabel="%s">\n' % \
			(string.join(self.name.split(' '), '-'), self.name)
		s += '<title>%s</title>\n' % self.name
		s += '<cmdsynopsis>\n'
		s += '\t<command>pragma %s</command>\n' % self.name
		for ((name, type, opt, rep), txt) in self.section['arg']:
			if opt:
				choice = 'opt'
			else:
				choice = 'req'
			if rep:
				repeat = 'repeat'
			else:
				repeat = 'norepeat'
			s += '\t<arg rep="%s" choice="%s">%s</arg>\n' % \
				(repeat, choice, name)
		for ((name, type, opt, rep), txt) in self.section['param']:
			if opt:
				choice = 'opt'
			else:
				choice = 'req'
			if rep:
				repeat = 'repeat'
			else:
				repeat = 'norepeat'
			s += '\t<arg rep="%s" choice="%s">' % (repeat, choice)
			s += '%s=<replaceable>%s</replaceable>' % (name, type)
			s += '</arg>\n'
		s += '</cmdsynopsis>\n'
		s += '<para>\n'
		s += saxutils.escape(self.section['description'])
		s += '\n</para>\n'
		if self.section['arg']:
			s += '<variablelist><title>arguments</title>\n'
			for ((name, type, opt, rep), txt) in \
				self.section['arg']:
				s += '\t<varlistentry>\n'
				if opt:
					term = '<optional>%s</optional>' % name
				else:
					term = name
				s += '\t<term>%s</term>\n' % term
				s += '\t<listitem>\n'
				s += '\t<para>\n'
				s += saxutils.escape(txt)
				s += '\n\t</para>\n'
				s += '\t</listitem>\n'
				s += '\t</varlistentry>\n'
			s += '</variablelist>\n'
		if self.section['param']:
			s += '<variablelist><title>parameters</title>\n'
			for ((name, type, opt, rep), txt) in \
				self.section['param']:
				s += '\t<varlistentry>\n'
				if opt:
					optStart = '<optional>'
					optEnd   = '</optional>'
				else:
					optStart = ''
					optEnd   = ''
				key = '%s=' % name
				val = '<replaceable>%s</replaceable>' % type
				s += '\t<term>%s%s%s%s</term>\n' % \
					(optStart, key, val, optEnd)
				s += '\t<listitem>\n'
				s += '\t<para>\n'
				s += saxutils.escape(txt)
				s += '\n\t</para>\n'
				s += '\t</listitem>\n'
				s += '\t</varlistentry>\n'
			s += '</variablelist>\n'
		if self.section['example']:
			s += '<variablelist><title>examples</title>\n'
			for (cmd, txt) in self.section['example']:
				s += '\t<varlistentry>\n'
				s += '\t<term>\n'
				if 'root' in self.users:
					s += '# '
				else:
					s += '$ '
				s += 'pragma %s' % cmd
				s += '\n\t</term>\n'
				s += '\t<listitem>\n'
				s += '\t<para>\n'
				s += saxutils.escape(txt)
				s += '\n\t</para>\n'
				s += '\t</listitem>\n'
				s += '\t</varlistentry>\n'
			s += '</variablelist>\n'
		if self.section['related']:
			s += '<variablelist><title>related commands</title>\n'
			for related in self.section['related']:
				s += '\t<varlistentry>\n'
				s += '\t<term>'
				s += '<xref linkend="pragma-%s">' % \
					string.join(related.split(' '), '-')
				s += '</term>\n'
				s += '\t<listitem>\n'
				s += '\t<para>\n'
				s += '\n\t</para>\n'
				s += '\t</listitem>\n'
				s += '\t</varlistentry>\n'
			s += '</variablelist>\n'
		s += '</section>'
		return s

	
	def getUsageText(self):
		s = ''
		for ((name, type, opt, rep), txt) in self.section['arg']:
			if opt:
				s += '[%s]' % name
			else:
				s += '{%s}' % name
			if rep:
				s += '...'
			s += ' '
		for ((name, type, opt, rep), txt) in self.section['param']:
			if opt:
				s += '[%s=%s]' % (name, type)
			else:
				s += '{%s=%s}' % (name, type)
			if rep:
				s += '...'
			s += ' '
		if s and s[-1] == ' ':
			return s[:-1]
		else:
			return s
	
	def getSphinxText(self):
		if 'root' in self.users:
			prompt = '#'
		else:
			prompt = '$'

		s  = ':orphan:\n\n'
		s += '%s\n' % self.name
		s += '%s\n\n' % ("-" * len(self.name))
		s += '.. role:: defn\n\n' 
		utxt = self.getUsageText()
		if len(utxt): 
		    s += ':defn:`pragma %s` *%s*\n' % (self.name, utxt)
		else:         
		    s += ':defn:`pragma %s` %s\n' % (self.name, utxt)
		s += '\n\n**Description:**\n'
		s += self.section['description'].replace('\t','   ')
		if self.section['arg']:
			s += '\n**Arguments:**\n\n'
			for ((name, type, opt, rep), txt) in \
				self.section['arg']:
				if opt:
					s += '*[%s]*' % name
				else:
					s += '*{%s}*' % name
				txt = txt.replace('*', '\*')
				s += '\n%s\n' % txt.replace('\t', '   ')
		if self.section['param']:
			s += '\n**Parameters:**\n\n'
			for ((name, type, opt, rep), txt) in \
				self.section['param']:
				if opt:
					s += '*[%s=%s]*' % (name, type)
				else:
					s += '*{%s=%s}*' % (name, type)
				txt = txt.replace('*', '\*')
				s += '\n%s\n' % txt.replace('\t', '   ')
		if self.section['example']:
			s += '\n**Examples:**\n'
			for (cmd, txt) in self.section['example']:
				txt = txt.replace('*', '\*')
				s += '%s::\n\n' % txt.replace('\t','   ')
				s += '        %s pragma %s\n' % (prompt, cmd)
		if self.section['related']:
			s += '\n**Related Commands:**\n\n'
			for related in self.section['related']:
				s += '   * :ref:`pragma-%s`\n' % related.replace(' ','-')

		word = self.name.split()[0]
		s += '\n:ref:`%s commands <%s-ref>`\n' % (word, word)

		return s

	def getPlainText(self):
		if 'root' in self.users:
			prompt = '#'
		else:
			prompt = '$'
		s  = ''
		s += 'pragma %s %s' % (self.name, self.getUsageText())
		s += '\n\nDescription:\n'
		s += self.section['description']
		if self.section['arg']:
			s += '\nArguments:\n\n'
			for ((name, type, opt, rep), txt) in \
				self.section['arg']:
				if opt:
					s += '\t[%s]' % name
				else:
					s += '\t{%s}' % name
				s += '\n%s\n' % txt
		if self.section['param']:
			s += '\nParameters:\n\n'
			for ((name, type, opt, rep), txt) in \
				self.section['param']:
				if opt:
					s += '\t[%s=%s]' % (name, type)
				else:
					s += '\t{%s=%s}' % (name, type)
				s += '\n%s\n' % txt
		if self.section['example']:
			s += '\nExamples:\n\n'
			for (cmd, txt) in self.section['example']:
				s += '\t%s pragma %s\n' % (prompt, cmd)
				s += '%s\n' % txt
		if self.section['related']:
			s += '\nRelated Commands:\n\n'
			for related in self.section['related']:
				s += '\tpragma %s\n' % related
		return s
		
	def getParsedText(self):
		return '%s' % self.section
		
	def startElement(self, name, attrs):
		if not self.section['description']:
			self.section['description'] = self.text
		self.key  = None
		self.text = ''
		if name in [ 'arg', 'param' ]:
			try:
				type = attrs.get('type')
			except:
				type = 'string'
			try:
				optional = int(attrs.get('optional'))
			except:
				if name == 'arg':
					optional = 0
				if name == 'param':
					optional = 1
			try:
				repeat = int(attrs.get('repeat'))
			except:
				repeat = 0
			name = attrs.get('name')
			self.key = (name, type, optional, repeat)
		elif name == 'example':
			self.key = attrs.get('cmd')
		
	def endElement(self, name):
		if name == 'docstring':
			# we are done so sort the param and related lists
			self.section['param'].sort()
			self.section['related'].sort()
		elif name in [ 'arg', 'param', 'example' ]:
			self.section[name].append((self.key, self.text))
		else:
			if self.section.has_key(name):
				self.section[name].append(self.text)
		
	def characters(self, s):
		self.text += s
			
			

class DatabaseConnection:

	"""Wrapper class for all database access.  The methods are based on
	those provided from the MySQLdb library and some other Rocks
	specific methods are added.  All RocksCommands own an instance of
	this object (self.db).
	
	Special Environment Variables:
	
	ROCKS_VARS_HOSTNAME	- If defined specified the Rocks host
				that all app_globals lookups are 
				relative to.  If unspecified the localhost
				is assumed.  All methods that use this
				also also the value to be passed as an
				argument.
	"""
	
	def __init__(self, db):
		# self.database : is a rocks.db.database.Database object
		self.database = db
		
	def execute(self, command):
		return self.database.execute(command)

	def fetchone(self):
		return self.database.fetchone()

	def fetchall(self):
		return self.database.fetchall()

	def getSession(self):
		"""helper function to get the session"""
		return self.database.getSession()

	def getHostRoutes(self, host, showsource=0):

		host = self.getHostname(host)
		routes = {}
		
		# global
		self.execute("""select network, netmask, gateway, subnet from
			global_routes""")
		for (n, m, g, s) in self.fetchall():
			if s:
				rows = self.execute("""select net.device from
					subnets s, networks net, nodes n where
					s.id = %s and s.id = net.subnet and
					net.node = n.id and n.name = '%s'
					and net.device not like 'vlan%%' """
					% (s, host))
				if rows == 1:
					g, = self.fetchone()
			
			if showsource:
				routes[n] = (m, g, 'G')
			else:
				routes[n] = (m, g)

		# os
		self.execute("""select r.network, r.netmask, r.gateway,
			r.subnet from os_routes r, nodes n where
			r.os=n.os and n.name='%s'"""  % host)
		for (n, m, g, s) in self.fetchall():
			if s:
				rows = self.execute("""select net.device from
					subnets s, networks net, nodes n where
					s.id = %s and s.id = net.subnet and
					net.node = n.id and n.name = '%s' 
					and net.device not like 'vlan%%' """
					% (s, host))
				if rows == 1:
					g, = self.fetchone()

			if showsource:
				routes[n] = (m, g, 'O')
			else:
				routes[n] = (m, g)

		# appliance		
		self.execute("""select r.network, r.netmask, r.gateway,
			r.subnet from
			appliance_routes r,
			nodes n,
			memberships m,
			appliances app where
			n.membership=m.id and m.appliance=app.id and 
			r.appliance=app.id and n.name='%s'""" % host)
		for (n, m, g, s) in self.fetchall():
			if s:
				rows = self.execute("""select net.device from
					subnets s, networks net, nodes n where
					s.id = %s and s.id = net.subnet and
					net.node = n.id and n.name = '%s' 
					and net.device not like 'vlan%%' """
					% (s, host))
				if rows == 1:
					g, = self.fetchone()

			if showsource:
				routes[n] = (m, g, 'A')
			else:
				routes[n] = (m, g)

		# host				
		self.execute("""select r.network, r.netmask, r.gateway,
			r.subnet from node_routes r, nodes n where
			n.name='%s' and n.id=r.node""" % host)
		for (n, m, g, s) in self.fetchall():
			if s:
				rows = self.execute("""select net.device from
					subnets s, networks net, nodes n where
					s.id = %s and s.id = net.subnet and
					net.node = n.id and n.name = '%s'
					and net.device not like 'vlan%%' """
					% (s, host))
				if rows == 1:
					g, = self.fetchone()

			if showsource:
				routes[n] = (m, g, 'H')
			else:
				routes[n] = (m, g)
			
		return routes

	def getHostAttrs(self, host, showsource=0):
		"""Return a dictionary of KEY x VALUE pairs for the host
		specific attributes for the given host.
		"""
		hostname = self.getHostname(host)
		return self.database.getHostAttrs(hostname, showsource)


	def getHostAttr(self, host, key):
		"""Return the value for the host specific attribute KEY or
		None if it does not exist.
		"""
		
		# This should be its own SQL but cheat until the code
		# stabilizes.
		
		return self.getHostAttrs(host).get(key)


	def getSecAttr(self, attr = None):
		""" Get a globally defined named, secure attribute """
		if attr is None:
			return {}
		attrs = {}
		self.execute('select value, enc from sec_global_attributes ' +\
			'where attr="%s"' % attr)
		for (v, e) in self.fetchone():
			attrs[attr] = (v, e)
		return attrs

	def getSecAttrs(self):
		""" Get all globally defined secure attribute """
		attrs = {}
		self.execute('select attr, value, enc from sec_global_attributes')
		for (a, v, e) in self.fetchall():
			attrs[a] = (v, e)

		return attrs

	def getHostSecAttrs(self, host):
		""" Get all secure attributes for a host """
		attrs = self.getSecAttrs() 

		self.execute('select s.attr, s.value, s.enc from sec_node_attributes s, nodes n ' +\
			'where s.node=n.id and n.name="%s"' % host)
		for (a, v, e) in self.fetchall():
			attrs[a] = (v, e)

		return attrs

	def getHostSecAttr(self, host, attr = None):
		""" Get named, secure attribute for a host """
		if attr is None:
			return {}

		attrs = self.getSecAttr(attr) 

		self.execute('select s.value, s.enc from sec_node_attributes s, nodes n ' +\
			'where s.attr="%s" s.node=n.id and n.name="%s"' % (attr, host))
		for (v, e) in self.fetchone():
			attrs[a] = (v, e)
	
		return attrs	

	def getHostname(self, hostname=None):
		"""Returns the name of the given host as referred to in
		the database.  This is used to normalize a hostname before
		using it for any database queries."""

		# moved in rocks.db.helper.DatabaseHelper
		return self.database.getHostname(hostname)


class Command:
	"""Base class for all Rocks commands the general command line form
	is as follows:

		rocks ACTION COMPONENT OBJECT [ <ARGNAME ARGS> ... ]
		
		ACTION(s):
			add
			create
			list
			load
			sync
	"""

	MustBeRoot = 0

	def __init__(self, database):
		"""Creates a DatabaseConnection for the RocksCommand to use.
		This is called for all commands, including those that do not
		require a database connection."""

		# DISABLE self.db = DatabaseConnection(database)
		# new database connection in rocks.db
		# soon (or later) self.db will be removed and only newdb will be left
		# DISABLE self.newdb = self.db.database

		self.text = ''
		
		self.output = []
        
		self.arch = os.uname()[4]
		if self.arch in [ 'i386', 'i486', 'i586', 'i686' ]:
			self.arch = 'i386'
		self.os = os.uname()[0].lower()

		self._args = None
		self._params = None
		if os.environ.has_key('ROCKSDEBUG'):
			self._debug = True
		else:
			self._debug = False


	def debug(self):
		"""return true if we are in debug mode"""
		return self._debug
		
	def abort(self, msg):
		syslog.syslog(syslog.LOG_ERR, msg.split('\n')[0])
		raise pragma.utils.CommandError(msg)
	
	def fillPositionalArgs(self, names, params=None, args=None):
		# The helper function will allow named parameters
		# to be used in lieu of positional arguments
		# Example:  
		#   Suppose command is of the form: 
                #            command <arg1> <arg2> <arg3>
		#   Usually called as:
		#            command foo bar baz
                #   However if you name the arguments as parameters, say
		#           arg1, arg2, arg3
		#   Then, equivalent calls of the command are
		#	    command arg1=foo arg2=bar arg3=baz 
		#           command foo arg2=bar arg3=baz
                #           command foo bar arg3=baz
		#           command foo bar baz
		#           command foo arg2=bar baz
		#
		#   Arguments:
		#           paramlist = list of parameter names in the order
		#                       that their unnamed argument counterparts
		#			 appear eg. paramlist=('iface','mac')
		#	    params    = list of parameters (e.g param=value) 
		#           args      = args
		#
		#  Returns:
		#           remaining args, Filled parameters
		#  Example:
		#           hostlist,iface,mac=self.fillPositionalArgs( \
	        #			('iface','mac'),params,args)
	
		if not type(names) in [ types.ListType, types.TupleType ]:
			names = [ names ]
			 
		if not params:
			params = self._params
		if not args:
			args = self._args
			
		list = []
		for name in names:
			if params.has_key(name):
				list.append(params[name])
			else:
				list.append(None)

		# now walk backwards through the args and pull off
		# positional arguments that have not already been set
		# as a param=<parameter>

		trimmedArgs = args
		vars = []
		list.reverse()
		for e in list:
			if not e and len(trimmedArgs):
				vars.append(trimmedArgs[-1])
				trimmedArgs = trimmedArgs[:-1]
			else:
				vars.append(e)
		
		# need to reverse the 'vars' to get them in the correct order
		# since we processed them above in reverse order
		vars.reverse()

		rlist=[]
		rlist.append(trimmedArgs)
		rlist.extend(vars)
		return rlist 

	def fillParams(self, names, params=None):
		"""Returns a list of variables with either default
		values of the values in the PARAMS dictionary.
		
		NAMES - list of (KEY, DEFAULT) tuples.
			KEY - key name of PARAMS dictionary
			DEFAULT - default value if key in not in dict
		PARAMS - optional dictionary
		
		For example:
		
		(svc, comp) = self.fillParams(
			('service', None),
			('component', None))
			
		Can also be written as:
		
		(svc, comp) = self.fillParams(('service',), ('component', ))
		"""

		# make sure names is a list or tuple
		
		if not type(names) in [ types.ListType, types.TupleType ]:
			names = [ names ]

		# for each element in the names list make sure it is also
		# a tuple.  If the second element (default value) is missing
		# use None.  The resulting PDLIST is a list of (key, default) 
		# tuples.
		
		pdlist = []
		for e in names:
			if type(e) in [ types.ListType, types.TupleType] \
				and len(e) == 2:
				tuple = ( e[0], e[1] )
			else:
				tuple = ( e[0], None )
			pdlist.append(tuple)
				
		if not params:
			params = self._params

		list = []
		for (key, default) in pdlist:
			if params.has_key(key):
				list.append(params[key])
			else:
				list.append(default)
		return list


	def command(self, command, args=[]):
		"""Import and run a Rocks command.
		Returns and output string."""

		modpath = 'pragma.commands.%s' % command
		__import__(modpath)
		mod = eval(modpath)

		try:
			o = getattr(mod, 'Command')(None) # DISABLE (self.newdb)
			name = string.join(string.split(command, '.'), ' ')
		except AttributeError:
			return ''

		# flash to the DB and expire any ORM object to avoid reading 
		# cached values in future DB query
		# DISABLE self.newdb.commit()

		o.runWrapper(name, args)
		return o.getText()


	def loadPlugins(self):
		dict	= {}
		graph	= pragma.graph.Graph()
		
		dir = eval('%s.__path__[0]' % self.__module__)
		for file in os.listdir(dir):
			if file.split('_')[0] != 'plugin':
				continue
			if os.path.splitext(file)[1] != '.py':
				continue
			module = '%s.%s' % (self.__module__,
				os.path.splitext(file)[0])
			__import__(module)
			module = eval(module)
			try:
				o = getattr(module, 'Plugin')(self)
			except AttributeError:
				continue
			
			# All nodes point to TAIL.  This insures a fully
			# connected graph, otherwise partial ordering
			# will fail

			if graph.hasNode(o.provides()):
				plugin = graph.getNode(o.provides())
			else:
				plugin = rocks.graph.Node(o.provides())
			dict[plugin] = o

			if graph.hasNode('TAIL'):
				tail = graph.getNode('TAIL')
			else:
				tail = rocks.graph.Node('TAIL')
			graph.addEdge(rocks.graph.Edge(plugin, tail))
			
			for pre in o.precedes():
				if graph.hasNode(pre):
					tail = graph.getNode(pre)
				else:
					tail = rocks.graph.Node(pre)
				graph.addEdge(rocks.graph.Edge(plugin, tail))
					
			for req in o.requires():
				if graph.hasNode(req):
					head = graph.getNode(req)
				else:
					head = rocks.graph.Node(req)
				graph.addEdge(rocks.graph.Edge(head, plugin))
			
		list = []
		for node in PluginOrderIterator(graph).run():
			if dict.has_key(node):
				list.append(dict[node])
		return list

		
	def runPlugins(self, args='', plugins=None):
		print "in runPlugins"
		return

		#if not plugins:
		#	plugins = self.loadPlugins()
		#for plugin in plugins:
                #        syslog.syslog(syslog.LOG_INFO, 'run %s' % plugin)
		#	plugin.run(args)


	def isRootUser(self):
		"""Returns TRUE if running as the root account."""
		if os.geteuid() == 0:
			return 1
		else:
			return 0
			
	def isApacheUser(self):
		"""Returns TRUE if running as the apache account."""
		try:
			if os.geteuid() == pwd.getpwnam('apache')[3]:
				return 1
		except:
			pass
		return 0
		
	
	def str2bool(self, s):
		"""Converts an on/off, yes/no, true/false string to 1/0.
		TODO remove me. This functions are now in rocks.util"""
		if s and s.upper() in [ 'ON', 'YES', 'Y', 'TRUE', '1' ]:
			return 1
		else:
			return 0

	def bool2str(self, b):
		"""Converts an 1/0 to a yes/no"""
		if b:
			return 'yes'
		else:
			return 'no'

	
	def strWordWrap(self, line, indent=''):
		if os.environ.has_key('COLUMNS'):
			cols = os.environ['COLUMNS']
		else:
			cols = 80
		l = 0
		s = ''
		for word in line.split(' '):
			if l + len(word) < cols:
				s += '%s ' % word
				l += len(word) + 1 # space
			else:
				s += '\n%s%s ' % (indent, word)
				l += len(indent) + len(word) + 1 # space
		return s
			
	def clearText(self):
		"""Reset the output text buffer."""
		self.text = ''
		
	def addText(self, s):
		"""Append a string to the output text buffer."""
		if s:
			self.text += s
		
	def getText(self):
		"""Returns the output text buffer."""
		return self.text	

	def beginOutput(self):
		"""Reset the output list buffer."""
		self.output = []


	def addOutput(self, owner, vals):
		"""Append a list to the output list buffer."""

		# VALS can be a list, tuple, or primitive type.
		list = [ '%s:' % owner ]

		if isinstance(vals, types.ListType):
			list.extend(vals)
		elif isinstance(vals, types.TupleType): 
			for e in vals:
				list.append(e)
		else:
			list.append(vals)
			
		self.output.append(list)
		
		
	def endOutput(self, header=[], padChar='-', trimOwner=1,linesep='\n'):
		"""Pretty prints the output list buffer."""

		# Handle the simple case of no output, and bail out
		# early.  We do this to avoid printing out nothing
		# but a header w/o any rows.
		
		if not self.output:
			return

		# check if the user has selected output-header=flase to
		# disable output of the header
		# or output-col to disable output of some column

		showHeader      = True
		if 'output-header' in self._params:
			showHeader = self.str2bool(self._params['output-header'])

		self.outputCols = []
		if 'output-col' in self._params:
			showCols = self._params['output-col'].split(',')
			for i in header:
				if i.lower() in showCols:
					self.outputCols.append(True)
				else:
					self.outputCols.append(False)
			
		# Loop over the output and check if there is more than
		# one owner (usually a hostname).  We have only one owner
		# there is no reason to display it.  The caller can use
		# trimOwner=0 to disable this optimization.

		if trimOwner:
			owner = ''
			self.startOfLine = 1
			for line in self.output:
				if not owner:
					owner = line[0]
				if not owner == line[0]:
					self.startOfLine = 0
		else:
			self.startOfLine = 0
				
		# Add the header to the output and start formatting.  We
		# keep the header optional and separate from the output
		# so the above decision (startOfLine) can be made.
		
		if header and showHeader:
			list = []
			for field in header:
				list.append(field.upper())
			output = [ list ]
			output.extend(self.output)
		else:
			output = self.output
			
		colwidth = []
		for line in output:
			for i in range(0, len(line)):
				if len(colwidth) <= i:
					colwidth.append(0)
				if type(line[i]) != types.StringType:
					if line[i] == None:
						itemlen = 0
					else:
						itemlen = len(repr(line[i]))
				else:
					itemlen = len(line[i])

				if itemlen > colwidth[i]:
					colwidth[i] = itemlen
				
		o = ''
		for line in output:
			list = []
			for i in range(self.startOfLine, len(line)):
				if line[i] == None:
					s = ''
				else:
					s = str(line[i])
				if padChar != '':
					if s:
						o = s.ljust(colwidth[i])
					else:
						o = ''.ljust(colwidth[i],
							padChar)
				else:
					o = s
				list.append(o)
			self.addText('%s%s' % (self.outputRow(list),linesep))


	def outputRow(self, list):
		if self.outputCols:
			l = []
			for i in range(0, len(list)):
				if self.outputCols[i + self.startOfLine]:
					l.append(list[i])
			return string.join(l, ' ')
		else:
			return string.join(list, ' ')



	def usage(self):
		if self.__doc__:
			handler = DocStringHandler()
			parser = make_parser()
			parser.setContentHandler(handler)
			try:
				parser.feed('<docstring>%s</docstring>' %
					self.__doc__)
			except:
				return '-- invalid doc string --'
			return handler.getUsageText()
		else:
			return '-- missing doc string --'

		
	def help(self, command, flags={}):
		if not self.__doc__:
			return

		if self.MustBeRoot:
			users = [ 'root', 'apache' ]
		else:
			users = []
			
		if flags.has_key('format'):
			format = flags['format'].lower()
		else:
			format = 'plain'
		
		if format == 'raw':
			i = 1
			for line in self.__doc__.split('\n'):
				self.addText('%d:%s\n' % (i, line))
				i += 1
		else:
			handler = DocStringHandler(command, users)
			parser = make_parser()
			parser.setContentHandler(handler)
			parser.feed('<docstring>%s</docstring>' % self.__doc__)
			if format == 'docbook':
				self.addText(handler.getDocbookText())
			elif format == 'parsed':
				self.addText(handler.getParsedText())
			elif format == 'sphinx':
				self.addText(handler.getSphinxText())
			else:
				self.addText(handler.getPlainText())

	
	def runWrapper(self, name, args):
		"""Performs various checks and logging on the command before 
		the run() method is called.  Derived classes should NOT
		need to override this."""

		username = pwd.getpwuid(os.geteuid())[0]
		if args:
			command = '%s %s' % (name, string.join(args,' '))
		else:
			command = name

		syslog.syslog(syslog.LOG_INFO,
			'user %s called "%s"' % (username, command))
			
		# Split the args and flags apart.  Args have no '='
		# with the exception of select statements (special case), and
		# flags have one or more '='.
		
		dict = {} # flags
		list = [] # arguments
		
		nparams = 0
		flagpattern=re.compile("^[a-zA-z0-9\-_+]+=")

		for arg in args:
			tokens = arg.split()
			if tokens[0] == 'select':
				list.append(arg)
			#there is an equal and 
			#the left side of the equal does not contains spaces
			elif flagpattern.match(arg):
				(key, val) = arg.split('=', 1)
				dict[key] = val
				if nparams == 0:
					dict['@ROCKSPARAM0']=arg
				nparams += 1
			else:
				list.append(arg)

		if list and list[0] == 'help':
			self.help(name, dict)
		else:
			if self.MustBeRoot and not \
				(self.isRootUser() or self.isApacheUser()):
				self.abort('command "%s" requires root' % name)
			else:
				self._args   = list
				self._params = dict
				try:
					self.run(self._params, self._args)
					# DISABLE if self.newdb is not None:
						# DISABLE self.newdb.commit()
				except pragma.utils.HostnotfoundException as e:
					if self.debug():
						traceback.print_exc()
					self.abort(str(e))



	def run(self, flags, args):
		"""All derived classes should override this method.
		This method is called by the rocks command line as the
		entry point into the Command object.
		
		flags: dictionary of key=value flags
		args: list of string arguments"""
		
		pass

		
class Plugin:
	"""Base class for all Rocks command plug-ins."""
	
	def __init__(self, command):
		self.owner = command
		#self.db    = command.db
		
	def provides(self):
		"""Returns a unique string to identify the plug-in.  All
		Plugins must override this method."""

		return None
		
	def requires(self):
		"""Returns a list of plug-in identifiers that must be
		run before this Plugin.  This is optional for all 
		derived classes."""

		return []

	def precedes(self):
		"""Returns a list of plug-in identifiers that can only by
		run after this Plugin.  This is optional for all derived
		classes."""

		return []
	
		
	def run(self, args):
		"""All derived classes should override this method. This
		is the entry point into the Plugin object."""
		
		pass



class sec_attr_plugin:
	"""Base Plugin class for processing secure attributes
	This is based on the 411 plugin architecture"""
	def __init__(self):
		pass

	def get_sec_attr(self):
		return None

	def filter(self, value = None):
		return None

RollName = "pragma_boot"
