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
		result = repository.listRepository()

		print "VIRTUAL IMAGE"
		for item in result:
			print item


RollName = "pragma_boot"
