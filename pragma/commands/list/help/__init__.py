import os
import string
import pragma.file
import pragma.commands


class Command(pragma.commands.list.command):
	"""
	The Help Command print the usage of all the registered
	Commands.
	
	<param optional='1' type='string' name='subdir'>
	Relative of Python commands for listing help.  This is used internally
	only.
	</param>
	
	<example cmd='list help'>
	List help for all commands
	</example>
	
	<example cmd='list help subdir=list/host'>
	List help for all commands under list/host
	</example>
	"""

	def run(self, params, args):

		# Because this command is called directly from the rock.py
		# code we need to provide the params argument.  This is the
		# only command where we need to include this argument.
		
		(subdir, cols) = self.fillParams([('subdir', ), ('cols', 80)], params)
		
		if subdir:
			filepath = os.path.join(pragma.commands.__path__[0], subdir)
			modpath = 'pragma.commands.%s' % \
				string.join(subdir.split(os.sep), '.')
		else:
			filepath = pragma.commands.__path__[0]
			modpath = 'pragma.commands'
		
		tree = pragma.file.Tree(filepath)
		dirs = tree.getDirs()
		dirs.sort()

		if 'COLUMNS' in os.environ:
			cols = os.environ['COLUMNS']
			
		for dir in dirs:
			if not dir:
				continue
				
			module = '%s.%s' % \
				(modpath, string.join(dir.split(os.sep), '.'))
			__import__(module)
			module = eval(module)
			
			try:
				o = getattr(module, 'Command')(None)
			except AttributeError:
				continue
		
			if o.MustBeRoot and not self.isRootUser():
				continue

			# Format the brief usage to fit within the
			# width of the user's window (default to 80 cols)
			
			cmd = string.join(dir.split(os.sep), ' ')
			l = len(cmd) + 1
			s = ''
			for arg in o.usage().split():
				if l + len(arg) < cols or cols == 0:
					s += '%s ' % arg
					l += len(arg) + 1  # space
				else:
					s += '\n\t%s ' % arg
					l = len(arg) + 9  # tab + space

			self.addText('%s %s\n' % (cmd, s))


RollName = "pragma_boot"
