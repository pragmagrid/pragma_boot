import pragma.commands
import pragma.utils


class Command(pragma.commands.list.command):
	"""
	List available virtual cluster images in repository

	<example cmd='list repository'>
	List available virtual clusters images
	</example>
	"""

	def run(self, params, args):
		repository = self.getRepository()
		vc_db_filepath = repository.get_vcdb_file()

		print "NAME"
		with open(vc_db_filepath, 'r') as vc_db:
			for line in vc_db:
				(vcname, xmlpath) = line.split(',')
				print vcname


RollName = "pragma_boot"
