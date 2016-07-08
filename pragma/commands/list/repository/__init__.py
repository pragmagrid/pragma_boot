import os
import pragma.commands
import pragma.drivers
import pragma.utils
import re
import sys


class Command(pragma.commands.list.command):
	"""
	List available virtual cluster images in repository

	<example cmd='list repository'>
	List available virtual clusters images
	</example>
	"""

	def run(self, params, args):
		(args, vcname) = self.fillPositionalArgs(('vc-name'))

		# Read in site configuration file and imports values: site_ve_driver
		execfile(self.siteconf, {}, globals())

		# load driver
		driver = self.importDriver(site_ve_driver)
		if not driver:
			self.abort("Uknown driver %s" % site_ve_driver)

		repository = self.getRepository()
		result = driver.listRepository(repository)

		print "VIRTUAL IMAGE"
		for item in result:
			print item

RollName = "pragma_boot"
