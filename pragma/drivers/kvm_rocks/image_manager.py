from datetime import datetime
import glob
import logging
import os
import pragma.utils
import re
import shutil
import socket

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
		elif 'volume' in frontend_disk and 'volume' in compute_disk:
			manager = ZfsImageManager(frontend_disk, compute_disk)
		else:
			logger.error("Unknown disk type in %s" % str(frontend_disk))
			return None
		manager.fe_name = frontend['name']
		manager.compute_names = compute_names
		manager.temp_dir = temp_dir
		manager.configure()
		return manager

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

	def create_compute_disks(self):
		pass

	def create_frontend_disk(self):
		pass

	def install_to_image(self, path, files):
		for file, dest in files.iteritems():
			new_path = os.path.join(path, dest.lstrip("/") )
			logger.info("Copying %s to %s" % (file, new_path))
			shutil.copyfile(file,new_path)

	def mount_compute(self, name):
		pass

	def mount_frontend(self):
		pass

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

	def stage_compute(self, node):
		pass

	def umount_image(self, path):
		(out, ec) = pragma.utils.getOutputAsList("umount %s" % path)
		if ec != 0:
			logger.error("Unable to umount %s" % path)
			return 0
		os.rmdir(path)
		

class ZfsImageManager(ImageManager):
	def __init__(self, fe_spec, compute_spec):
		self.frontend = fe_spec
		self.compute = compute_spec
		self.our_phy_frontend = socket.gethostname().split(".")[0]

	def configure_zfs(self, name, zfs_spec):
		logger.info("Cloning %s" % name)
		clonename = "tmpclone-%s-%s" % (name, pragma.utils.get_id())

		(out, ec) = pragma.utils.getOutputAsList(
  			"ssh %s zfs snapshot %s@%s" % (
				zfs_spec['host'], zfs_spec['volume'], 
				clonename))
		if ec != 0:
			logger.error("Unable to snapshot %s" % zfs_spec['volume'])
			return

		(out, ec) = pragma.utils.getOutputAsList(
			"ssh %s zfs clone %s@%s %s/%s-vol" % (
				zfs_spec['host'], zfs_spec['volume'], 
				clonename, zfs_spec['pool'], name))
		if ec != 0:
			logger.error("Unable to clone %s" % zfs_spec['volume'])
			return

		(out, ec) = pragma.utils.getRocksOutputAsList(
			"set host vm nas %s nas=%s zpool=%s" % (
				name, zfs_spec['host'], zfs_spec['pool']))
		if ec != 0:
			logger.error("Unable to set nas for %ss" % name)
			return

	def create_compute_disks(self):
		for name in self.compute_names:
			self.configure_zfs(name, self.compute)

	def create_frontend_disk(self):
		self.configure_zfs(self.fe_name, self.frontend)

	def mount_compute(self, name):
		return self.mount_from_nas(name, self.compute)

	def mount_frontend(self):
		return self.mount_from_nas(self.fe_name, self.frontend)

	def mount_from_nas(self, name, zfs_spec):
		# remote mount image to our phy frontend
		(out, ec) = pragma.utils.getRocksOutputAsList(
			"add host storagemap %s %s %s-vol %s 10 img_sync=false" % (
				zfs_spec['host'], zfs_spec['pool'], 
				name, self.our_phy_frontend ))
		if ec != 0:
			logger.error("Unable to map for %s" % name)

		# get local mount
		(out, ec) = pragma.utils.getRocksOutputAsList(
        		"list host storagedev %s" % self.our_phy_frontend) 
		storagedev_pat = re.compile("^vol\S+\s+\S+\s+\S+\s+(\S+)");
		for line in out:
			result = storagedev_pat.search(line)
			if result:
				self.disks[name] = "/dev/%s" % result.group(1)

		# mount volume
		return self.mount_image(self.disks[name])

	def umount_compute(self, compute_mnt, name):
		self.umount_from_nas(compute_mnt, name, self.compute)

	def umount_frontend(self, fe_mnt):
		self.umount_from_nas(fe_mnt, self.fe_name, self.frontend)

	def umount_from_nas(self, mnt, name, zfs_spec):
		# unmount volume
                self.umount_image(mnt)

		# unmount from nas 
		(out, ec) = pragma.utils.getRocksOutputAsList(
			"remove host storagemap %s %s-vol" % (
				zfs_spec['host'], name))
		if ec != 0:
			logger.error("Unable to remove storagemap for %s" % name)

class NfsImageManager(ImageManager):
	SET_DISK_CMD = "set host vm %s disk=\"file:%s/%s.vda,vda,virtio\"" 
	SPARSE_CP_CMD = "cp --sparse=always %s %s" 

	def __init__(self, fe_img, compute_img, vc_dir, kvm_dir):
		self.frontend_img = fe_img
		self.compute_img = compute_img
		self.vc_dir = vc_dir
		self.diskdir = kvm_dir
		self.tmp_compute_img = None

	def configure(self):
		ImageManager.configure(self)
		if self.diskdir: 
			self.set_rocks_disk_paths()

	def create_frontend_disk(self):

                #uncompress "$fe_source_disk" "$temp_path/${fe_disk_path%.gz}"
		(out, ec) = pragma.utils.getOutputAsList(self.SPARSE_CP_CMD % (
				os.path.join(self.vc_dir, self.frontend_img), 
				self.disks[self.fe_name]))
		if ec != 0:
			logger.error("Problem copying frontend image: %s" % (
				"\n".join(out)))
			return 0
		return 1

	def create_compute_disks(self):
		self.tmp_compute_img = os.path.join(self.temp_dir, "compute.img")

		(out, ec) = pragma.utils.getOutputAsList(self.SPARSE_CP_CMD % (
				os.path.join(self.vc_dir, self.compute_img), 
				self.tmp_compute_img))
		if ec != 0:
			logger.error("Problem copying temp image %s: %s" % (
				self.tmp_compute_img,
				"\n".join(out)))

	def mount_compute(self, name):
		return self.mount_image(self.tmp_compute_img)

	def mount_frontend(self):
		return self.mount_image(self.disks[self.fe_name])

	def umount_compute(self, compute_mnt, name):
                self.umount_image(compute_mnt)

	def umount_frontend(self, fe_mnt):
                self.umount_image(fe_mnt)

	def stage_compute(self, node):
               	(out, ec) = pragma.utils.getOutputAsList(
			"rsync -S %s %s:%s" % (self.tmp_compute_img, self.phy_hosts[node], self.disks[node]))
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
