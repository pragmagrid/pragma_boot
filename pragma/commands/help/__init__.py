import string
import pragma.commands

class command(pragma.commands.Command):

	MustBeRoot = 0

	
class Command(command):
	"""
	List help for the command line client.  With no arguments it lists
	all the commands available.  Otherwise it will list the subset
	of command with the specified string (see examples).

	<arg type='string' name='command'>
	The substring matched against all commands.
	</arg>

	<example cmd='boot'>
	Alias for 'pragma boot help'
	</example>

	<example cmd='help agent'>
	Lists all the commands with the string 'agent' in the name.
	</example>

	<example cmd='help boot vm'>
	Lists all the commands with the string 'boot vm' in the name.
	</example>
	"""

	def run(self, params, args):

		help = self.command('list.help', [ 'cols=0' ])
		sub  = string.join(args)

		if not args:
			self.addText(help)
		else:
			for line in help.split('\n'):
				if line:
					if string.find(line, sub) >= 0:
						self.addText('%s\n' % line)
		

RollName = "pragma_boot"
