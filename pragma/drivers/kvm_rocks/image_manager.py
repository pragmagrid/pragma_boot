from datetime import datetime
import glob
import logging
import os
import pragma.utils
import re
import shutil

logger = logging.getLogger('pragma.drivers.kvm_rocks.image_manager')

class ImageManager:
	temp_dir = None

	@staticmethod
	def factory(vc_in, vc_out, temp_dir):
		frontend = vc_out.get_frontend()
		frontend_disk = vc_in.get_disk('frontend')
		compute_names = vc_out.get_compute_names()
		compute_disk = vc_in.get_disk('compute')
		manager = None
		if 'file' in frontend_disk and 'file' in compute_disk:
			manager = NfsImageManager(
				frontend_disk['file'], compute_disk['file'], 
				vc_in.dir, vc_out.get_kvm_diskdir())
		elif 'volume' in frontend and 'volume' in compute:
			manager = ZfsImageManager(
				fe_name, compute_names, frontend, compute)
		else:
			logger.error("Unknown disk type in %s" % str(frontend_disk))
			return None
		manager.fe_name = frontend['name']
		manager.compute_names = compute_names
		manager.temp_dir = temp_dir
		manager.configure()
		return manager

	def copy_frontend_disk(self):
		pass

	def install_to_image(self, path, files):
		for file, dest in files.iteritems():
			new_path = os.path.join(path, dest.lstrip("/") )
			logger.info("Copying %s to %s" % (file, new_path))
			shutil.copyfile(file,new_path)

	def mount_image(self, path):
		image_name = os.path.basename(path)
		temp_mnt_dir = os.path.join(self.temp_dir, "mnt-%s" % image_name)
		if not os.path.exists(temp_mnt_dir):
			logger.info("Making mount dir %s" % temp_mnt_dir)
			os.mkdir(temp_mnt_dir)
		(out, ec) = pragma.utils.getOutputAsList( 
			"guestmount -a %s -i %s" % (path, temp_mnt_dir))
		if ec != 0:
			logger.error("Problem mounting %s: %s" % (
				path, "\n".join(out)))
			os.remove(temp_mnt_dir)
		return temp_mnt_dir

	def safe_remove_from_image(self, path, file_patterns):
		for file_pat in file_patterns:
			abs_file_pat = os.path.join(path,file_pat.lstrip("/"))
			logger.debug( "Checking for file(s) %s" % abs_file_pat)
			for file in glob.glob(abs_file_pat):
				file_basename = os.path.basename(file)
				file_dir = os.path.dirname(file)
				oldfile = os.path.join(
					file_dir, "old-%s" % file_basename)
				logger.info("Moving %s to %s" % (file, oldfile))
				os.rename(file, oldfile)

	def umount_image(self, path):
		(out, ec) = pragma.utils.getOutputAsList("umount %s" % path)
		if ec != 0:
			logger.error("Unable to umount %s" % path)
			return 0
		os.rmdir(path)
		

class ZfsImageManager(ImageManager):
	def __init__(self, fe_name, compute_names, fe_spec, compute_spec):
		self.nodes = [fe_name] + compute_names

	def copy_frontend_disk(self):
		pass

class NfsImageManager(ImageManager):
	SET_DISK_CMD = "set host vm %s disk=\"file:%s/%s.vda,vda,virtio\"" 
	SPARSE_CP_CMD = "cp --sparse=always %s %s" 

	def __init__(self, fe_img, compute_img, vc_dir, kvm_dir):
		self.frontend_img = fe_img
		self.compute_img = compute_img
		self.vc_dir = vc_dir
		self.diskdir = kvm_dir

	def configure(self):
		self.phy_hosts = {}
		self.disks = {}
               	(out, ec) = pragma.utils.getRocksOutputAsList(
			"list host vm showdisks=true")
		host_pat = re.compile("^(\S*%s\S*):\s+\d+\s+\d+\s+\d+\s+\S+\s+(\S+)\s+\S+\s+file:(\S+),vda,virtio" % self.fe_name)
		for line in out:
			result = host_pat.search(line)
			if result:
				self.phy_hosts[result.group(1)] = result.group(2)
				self.disks[result.group(1)] = result.group(3)
		if self.diskdir: 
			self.set_rocks_disk_paths()

	def copy_frontend_disk(self):

                #uncompress "$fe_source_disk" "$temp_path/${fe_disk_path%.gz}"
		(out, ec) = pragma.utils.getOutputAsList(self.SPARSE_CP_CMD % (
				os.path.join(self.vc_dir, self.frontend_img), 
				self.disks[self.fe_name]))
		if ec != 0:
			logger.error("Problem copying frontend image: %s" % (
				"\n".join(out)))
			return 0
		return 1

	def create_compute_disk(self):
		compute_img = os.path.join(self.temp_dir, "compute.img")

		(out, ec) = pragma.utils.getOutputAsList(self.SPARSE_CP_CMD % (
				os.path.join(self.vc_dir, self.compute_img), 
				compute_img))
		if ec != 0:
			logger.error("Problem copying temp image %s: %s" % (
				compute_img,
				"\n".join(out)))
			return None
		return compute_img

	def scp_image(self, compute_image, node):
               	(out, ec) = pragma.utils.getOutputAsList(
			"rsync -S %s %s:%s" % (compute_image, self.phy_hosts[node], self.disks[node]))
		if ec != 0:
			logger.error("scp command failed: %s" % ("\n".join(out)))

	def set_rocks_disk_paths(self):
		for node in [self.fe_name] + self.compute_names:
               		(out, ec) = pragma.utils.getOutputAsList(
				"ssh %s ls %s" % (self.phy_hosts[node],self.diskdir))
			if ec != 0:
				logger.error("%s does not exist on %s" % (
					self.diskdir, self.phy_hosts[node]))
				continue
               		(out, ec) = pragma.utils.getRocksOutputAsList(
                       		 self.SET_DISK_CMD % (node, self.diskdir, node))
