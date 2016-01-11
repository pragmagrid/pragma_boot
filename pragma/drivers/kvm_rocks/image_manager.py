import glob
import logging
import os
import pragma.utils
import re
import shutil
import socket

logger = logging.getLogger('pragma.drivers.kvm_rocks.image_manager')


class ImageManager:
	LIST_VM_PATTERN = "^(\S*%s\S*):\s+\d+\s+\d+\s+\d+\s+\S+\s+(\S+)\s+\S+\s+file:(\S+),vda,virtio"

	def __init__(self, fe_name):
		"""
		Initiate common private vars

		:return:
		"""
		self.fe_name = fe_name
		self.compute_names = []
		self.temp_dir = None
		self.phy_hosts = {}
		self.disks = {}
		(out, ec) = pragma.utils.getRocksOutputAsList(
			"list host vm showdisks=true")
		host_pat = re.compile(self.LIST_VM_PATTERN % self.fe_name)
		for line in out:
			result = host_pat.search(line)
			if result:
				self.phy_hosts[result.group(1)] = result.group(2)
				self.disks[result.group(1)] = result.group(3)

	def cleanup(self):
		"""
		Cleanup any temporary state
		"""
		pass

	@staticmethod
	def factory(vc_in, vc_out, temp_dir):
		"""
		Create an ImageManager instance based on the type on the cluster
		images.  Currently supports NSF and ZFS based volumes.

		:param vc_in:  Definition of a virtual cluster that can be instantiated
		:param vc_out:  Network information for new cluster
		:param temp_dir:  Path to temporary directory
		:return:  An instance of ImageManager
		"""
		frontend = vc_out.get_frontend()
		frontend_disk = vc_in.get_disk('frontend')
		compute_names = vc_out.get_compute_names()
		compute_disk = vc_in.get_disk('compute')
		manager = None
		if 'file' in frontend_disk and 'file' in compute_disk:
			manager = NfsImageManager(frontend['name'],
				frontend_disk['file'], compute_disk['file'], 
				vc_in.dir, vc_out.get_kvm_diskdir())
		elif 'volume' in frontend_disk and 'volume' in compute_disk:
			manager = ZfsImageManager(frontend['name'], frontend_disk, compute_disk)
		else:
			logger.error("Unknown disk type in %s" % str(frontend_disk))
			return None
		manager.compute_names = compute_names
		manager.temp_dir = temp_dir
		return manager

	def install_to_image(self, path, files):
		"""
		Copy files to mounted image

		:param path: Path to mounted image
		:param files: Hash array of files where key is the source and value is
						the path on the mounted image
		:return:
		"""
		for filename, dest in files.iteritems():
			new_path = os.path.join(path, dest.lstrip("/"))
			logger.info("Copying %s to %s" % (filename, new_path))
			shutil.copyfile(filename, new_path)

	def mount_image(self, path):
		"""
		Mount specified image to a temporary mount point

		:param path: Path to image volume
		:return:  Path to temporary mount point
		"""
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

	def prepare_compute(self, node, delete_spec, install_spec):
		"""
		Prepare compute node of new virtual cluster for booting

		:param node: Name of compute node to boot
		:param delete_spec: Array of files to delete on image
		:param install_spec: Hash array of file to install on image
		:return:
		"""
		raise "Unimplemented for ImageManager, %s" % self.__class__.__name__

	def prepare_frontend(self, delete_spec, install_spec):
		"""
		Prepare frontend of new virtual cluster for booting

		:param delete_spec: Array of files to delete on image
		:param install_spec: Hash array of file to install on image
		:return:
		"""
		raise "Unimplemented for ImageManager, %s" % self.__class__.__name__

	def safe_remove_from_image(self, path, file_patterns):
		"""
		Remove specified files from mounted image

		:param path: Path to mounted image
		:param file_patterns: array of file patterns to delete on mounted image
		:return:
		"""
		for file_pat in file_patterns:
			abs_file_pat = os.path.join(path, file_pat.lstrip("/"))
			logger.debug("Checking for file(s) %s" % abs_file_pat)
			for filename in glob.glob(abs_file_pat):
				file_basename = os.path.basename(filename)
				file_dir = os.path.dirname(filename)
				oldfile = os.path.join(
					file_dir, "old-%s" % file_basename)
				logger.info("Moving %s to %s" % (filename, oldfile))
				os.rename(filename, oldfile)

	def umount_image(self, path):
		"""
		Unmount image at specified path

		:param path: Path to mounted image
		:return:
		"""
		(out, ec) = pragma.utils.getOutputAsList("umount %s" % path)
		if ec != 0:
			logger.error("Unable to umount %s" % path)
			return 0
		os.rmdir(path)
		

class ZfsImageManager(ImageManager):
	def __init__(self, fe_name, fe_spec, compute_spec):
		"""
		Create an ImageManager for a ZFS based virtual cluster

		:param fe_spec: Information on virtual cluster frontend image
		:param compute_spec: Information on virtual cluster compute image
		:return:
		"""
		ImageManager.__init__(self, fe_name)
		self.frontend = fe_spec
		self.compute = compute_spec
		self.our_phy_frontend = socket.gethostname().split(".")[0]

	def clone_and_set_zfs_image(self, name, zfs_spec):
		"""
		Clone specified image of virtual cluster and set it in new virtual
		cluster.

		:param name: Name of virtual cluster node to clone and set in rocks db
		:param zfs_spec: ZFS information on source image
		:return:
		"""
		logger.info("Cloning %s" % name)
		clonename = "tmpclone-%s-%s" % (name, pragma.utils.get_id())

		(out, ec) = pragma.utils.getOutputAsList("ssh %s zfs snapshot %s@%s" % (
				zfs_spec['host'], zfs_spec['volume'], clonename))
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

	def mount_from_nas(self, vol, zfs_spec):
		"""
		Mount specified volume from NAS device

		:param vol:  Name of volume existing on NAS device
		:param zfs_spec:  ZFS info on specified virtual cluster node
		:return:
		"""
		# remote mount image to our phy frontend
		(out, ec) = pragma.utils.getRocksOutputAsList(
			"add host storagemap %s %s %s-vol %s 10 img_sync=false" % (
			zfs_spec['host'], zfs_spec['pool'], vol, self.our_phy_frontend))
		if ec != 0:
			logger.error("Unable to map for %s" % vol)

		# get local mount
		(out, ec) = pragma.utils.getRocksOutputAsList(
			"list host storagedev %s" % self.our_phy_frontend)
		storagedev_pat = re.compile("^vol\S+\s+\S+\s+\S+\s+(\S+)")
		for line in out:
			result = storagedev_pat.search(line)
			if result:
				self.disks[vol] = "/dev/%s" % result.group(1)

		# mount volume
		return self.mount_image(self.disks[vol])

	def prepare_compute(self, node, delete_spec, install_spec):
		"""
		Clone compute ZFS image and mount it to frontend.  Modify image with
		network configuration and then unmount image so it's ready to be booted.

		:param node: Name of compute node to boot
		:param delete_spec: Array of files to delete on image
		:param install_spec: Hash array of file to install on image
		:return:
		"""
		self.clone_and_set_zfs_image(node, self.compute)
		compute_mnt = self.mount_from_nas(node, self.compute)
		self.safe_remove_from_image(compute_mnt, delete_spec)
		self.install_to_image(compute_mnt, install_spec)
		self.umount_from_nas(compute_mnt, node, self.compute)

	def prepare_frontend(self, delete_spec, install_spec):
		"""
		Clone frontend ZFS image and mount it to frontend.  Modify image with
		network configuration and then unmount image so it's ready to be booted.

		:param delete_spec: Array of files to delete on image
		:param install_spec: Hash array of file to install on image
		:return:
		"""
		self.clone_and_set_zfs_image(self.fe_name, self.frontend)
		fe_mnt = self.mount_from_nas(self.fe_name, self.frontend)
		self.safe_remove_from_image(fe_mnt, delete_spec)
		self.install_to_image(fe_mnt, install_spec)
		self.umount_from_nas(fe_mnt, self.fe_name, self.frontend)

	def umount_from_nas(self, mnt, name, zfs_spec):
		"""
		Unmount volume from local temp directory and unmount volume from NAS

		:param mnt: Path to local directory for mounted volume
		:param name:  Name of node
		:param zfs_spec: ZFS info on node type
		:return:
		"""
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

	def __init__(self, fe_name, fe_img, compute_img, vc_dir, kvm_dir):
		"""
		Create an ImageManager for a NFS based virtual cluster

		:param fe_name: Name of virtual cluster frontend
		:param fe_img: Path to frontend image
		:param compute_img: Path to compute image
		:param vc_dir: Path to virtual cluster spec directory
		:param kvm_dir: Path to Rocks dir where virtual cluster imgs are stored
		:return:
		"""
		ImageManager.__init__(self, fe_name)
		self.frontend_img = fe_img
		self.compute_img = compute_img
		self.vc_dir = vc_dir
		self.diskdir = kvm_dir
		self.tmp_compute_img = None
		if self.diskdir:
			self.set_rocks_disk_paths()

	def cleanup(self):
		"""
		Cleanup any temporary state
		"""
		os.remove(self.tmp_compute_img)

	def create_tmp_compute(self):
		"""
		Create a copy of compute image that can be modifed

		:return:
		"""
		self.tmp_compute_img = os.path.join(self.temp_dir, "compute.img")

		(out, ec) = pragma.utils.getOutputAsList(self.SPARSE_CP_CMD % (
				os.path.join(self.vc_dir, self.compute_img), 
				self.tmp_compute_img))
		if ec != 0:
			logger.error("Problem copying temp image %s: %s" % (
				self.tmp_compute_img,
				"\n".join(out)))

	def prepare_compute(self, node, delete_spec, install_spec):
		"""
		Create a copy of specified compute image if needed, mount it and install
		new network configuration. Unmount volume and copy it over to
		remote node.

		:param node: Name of compute node to boot
		:param delete_spec: Array of files to delete on image
		:param install_spec: Hash array of file to install on image
		:return:
		"""
		if self.tmp_compute_img is None:
			self.create_tmp_compute()
		compute_mnt = self.mount_image(self.tmp_compute_img)
		self.safe_remove_from_image(compute_mnt, delete_spec)
		self.install_to_image(compute_mnt, install_spec)
		self.umount_image(compute_mnt)
		(out, ec) = pragma.utils.getOutputAsList("rsync -S %s %s:%s" % (
			self.tmp_compute_img, self.phy_hosts[node], self.disks[node]))
		if ec != 0:
			logger.error("scp command failed: %s" % ("\n".join(out)))

	def prepare_frontend(self, delete_spec, install_spec):
		"""
		Create a copy of specified frontend image, mount it and install
		new network configuration. Unmount volume.

		:param delete_spec: Array of files to delete on image
		:param install_spec: Hash array of file to install on image
		:return:
		"""
		(out, ec) = pragma.utils.getOutputAsList(self.SPARSE_CP_CMD % (
				os.path.join(self.vc_dir, self.frontend_img),
				self.disks[self.fe_name]))
		if ec != 0:
			logger.error("Problem copying frontend image: %s" % (
				"\n".join(out)))
			return 0
		fe_mnt = self.mount_image(self.disks[self.fe_name])
		self.safe_remove_from_image(fe_mnt, delete_spec)
		self.install_to_image(fe_mnt, install_spec)
		self.umount_image(fe_mnt)

	def set_rocks_disk_paths(self):
		"""
		Set alternate location to store KVM disks for Rocks virtual clusters
		:return:
		"""
		for node in [self.fe_name] + self.compute_names:
			(out, ec) = pragma.utils.getOutputAsList(
				"ssh %s ls %s" % (self.phy_hosts[node], self.diskdir))
			if ec != 0:
				logger.error("%s does not exist on %s" % (
					self.diskdir, self.phy_hosts[node]))
				continue
			pragma.utils.getRocksOutputAsList(
				self.SET_DISK_CMD % (node, self.diskdir, node))
