import logging

logger = logging.getLogger('pragma.drivers')

class Driver:
	def __init__(self):
		raise Exception("Unable to create an instance of abstract class %s" % self)

	@staticmethod
	def factory(driver_name):
		driver_class = 'pragma.drivers.%s.Driver' % driver_name
		logger.info( "Loading driver %s" % driver_class )
		fullpath = driver_class.split(".")
		from_module = ".".join(fullpath[:-1])
		classname = fullpath[-1]
 		module = __import__(from_module, fromlist=[classname])
		klass = getattr(module, classname)
		return klass()

	def allocate(self, cpus, memory, key, vc_in, vc_out, repository):
		pass

	def deploy_virtual_node(self):
		pass

	def start_cluster(self):
		self.allocate()
		self.deploy_virtual_node("frontend")
		# for my node in nodes:
				# self.deploy_virtual_node("node")
