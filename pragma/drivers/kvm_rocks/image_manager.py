import glob
import logging
import os
import pragma.utils
import re
import shutil
import socket
import sys
import time

logger = logging.getLogger('pragma.drivers.kvm_rocks.image_manager')


class ImageManager:
	LIST_VM_PATTERN = "^(\S*%s\S*)?:?\s*\d+\s+\d+\s+\d+\s+\S+\s+(\S+)\s+\S+\s+file:(\S+),vda,virtio"
	LIST_DISK_PATTERN = "^(\S*%s\S*)?:?\s*\d+\s+\d+\s+\d+\s+\S+\s+(\S+)\s+\S+\s+(\S+),vda,virtio"

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
				node = result.group(1)
				if not node: # single VM case
					node = self.fe_name
				self.phy_hosts[node] = result.group(2)
				self.disks[node] = result.group(3)

	def boot_cleanup(self):
		"""
		Cleanup any temporary state
		"""
		pass

	@staticmethod
	def clean_disk(node, disk_spec, host):
		"""
		Clean out the disk of the specified node.

		:param node: Name of node disk is being cleaned for
		:param disk_spec: Disk spec from the Rocks db
		:param host: Hostname of the VM container
		:return: True if disk is cleaned, otherwise false
		"""
		if re.search("^file", disk_spec):
			return NfsImageManager.clean_disk(node, disk_spec, host)
		elif re.search("^phy:/dev/mapper/", disk_spec):
			return ZfsImageManager.clean_disk(node, disk_spec, host)
		else:
			sys.stderr.write("Unable to clean disks of type %s\n" % disk_spec)
			return False

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

	@staticmethod
	def get_disks(vcname):
		"""
		Get disks for specified virtual cluster

		:param vcname: Name of virtual cluster

		:return: Hash array where key is the name of the node and
			value is the disk 
		"""
		disks = {}
		(out, ec) = pragma.utils.getRocksOutputAsList(
			"list host vm showdisks=true")
		host_pat = re.compile(ImageManager.LIST_DISK_PATTERN % vcname)
		for line in out:
			result = host_pat.search(line)
			if result:
				node = result.group(1)
				if not node: # single VM case
					node = vcname
				disks[node] = result.group(3)
		return disks

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

	@staticmethod
	def wait_for_disk(node, disk):
		"""
		Wait for disk for node to be unmounted

		:param path: Name of node to check disk

		:return: True if unmounted; otherwise False
		"""
		if re.search("^file", disk):
			pass
		elif re.search("^phy:/dev/mapper/", disk):
			return ZfsImageManager.wait_for_disk(node, disk)
		else:
			sys.stderr.write("Unable to wait for disk of type %s\n" % disk)
			return False

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
	SLEEP_FOR_UNMAPPED = 5

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

	@staticmethod
	def clean_disk(node, disk_spec, host):
		"""
		Clean out the specified disk on the VM container.

		:param disk_spec: Disk spec from the Rocks db
		:param host: Hostname of the VM container
		:return: True if disk is cleaned, otherwise false
		"""
		status = ZfsImageManager.get_disk_status(node, disk_spec)
		if status != 'unmapped': 
			sys.stderr.write("Volume %s is still mapped, cannot be removed yet\n" % disk_spec)
			return False
		(vol, pool, nas) = ZfsImageManager.get_nas_info(node, disk_spec)

		# remove volume
		print "  Removing %s from %s" % (vol, nas)
		(out, exitcode) = pragma.utils.getOutputAsList(
			"ssh %s zfs destroy -r %s" % (nas, vol))
		if exitcode != 0:
			sys.stderr.write("Problem removing vol %s for %s: %s\n" % (
				vol, node, "\n".join(out)))
			return False
		return True

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
			logger.error("Unable to set nas for %s" % name)
			return

		(out, ec) = pragma.utils.getOutputAsList(
			"ssh %s zfs get volsize %s" % (
				zfs_spec['host'], zfs_spec['volume']))
		if ec != 0:
			logger.error("Problem querying volsize for %s" % zfs_spec['volume'])
			return
		volsize = 0
		for line in out:
			result = re.search("%s+\s+\S+\s+(\d+)" % zfs_spec['volume'], line)
			if result != None:
				volsize = result.group(1)
		if volsize <= 0:
			logger.error("Unable to get volsize for %s" % zfs_spec['volume'])
			return

		(out, ec) = pragma.utils.getRocksOutputAsList(
			"set host vm %s disksize=%s" % (
				name, volsize))
		if ec != 0:
			logger.error("Unable to set disksize for %s" % name)
			return

	@staticmethod
	def get_disk_status(node, disk):
		"""
		Get the disk status for specified node

		:param node: Name of node to get status for disk
		:param disk: Disk spec from the Rocks db

		:return: Status of disk
		"""
		(vol, pool, nas) = ZfsImageManager.get_nas_info(node, disk)

		# check that volume has been unmapped
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
			"list host storagemap %s" % nas)
		if exitcode != 0:
			sys.stderr.write("Problem querying status of nas %s: %s\n" % (
				nas, "\n".join(out)))
			return False
		for line in out:
			result = re.search("^%s-vol\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)\s+" % node, line)
			if result is not None:
				return result.group(1)
		return None

	@staticmethod
	def get_nas_info(node, disk):
		"""
		Get the disk status for specified node

		:param node: Name of node to get status for disk
		:param disk: Disk spec from the Rocks db

		:return: Status of disk
		"""
		(out, exitcode) = pragma.utils.getRocksOutputAsList(
			"list host vm nas %s" % node)
		if exitcode != 0:
			sys.stderr.write("Problem querying nas for %s: %s\n" % (
				host, "\n".join(out)))
			return False
		out.pop(0) # pop off header
		(nas, pool) = re.split("\s+", out[0])
		vol = "%s/%s-vol" % (pool, node)
		return (vol, pool, nas)

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
		storagedev_pat = re.compile("^vol\S+\s+\S+\s+\S+%s-%s-vol\s+(\S+)" % (zfs_spec['host'], vol))
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

	@staticmethod
	def wait_for_disk(node, disk):
		"""
		Wait for disk for node to be unmapped

		:param path: Name of node to check disk

		:return: True if unmapped; otherwise False
		"""
	        status = ZfsImageManager.get_disk_status(node, disk)
		while status != 'unmapped':
			print "  Status of disk for node %s is %s; sleep for %i secs" % (
				node, status, ZfsImageManager.SLEEP_FOR_UNMAPPED)
			time.sleep(ZfsImageManager.SLEEP_FOR_UNMAPPED)
			status = ZfsImageManager.get_disk_status(node, disk)
		print "  Disk for node %s is %s" % (node, status)


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

	def boot_cleanup(self):
		"""
		Cleanup any temporary state
		"""
		if self.tmp_compute_img is not None:
			os.remove(self.tmp_compute_img)

	@staticmethod
	def clean_disk(node, disk_spec, host):
		"""
		Clean out the specified disk on the VM container.

		:param node: Name of node disk is being cleaned for
		:param disk_spec: Disk spec from the Rocks db
		:param host: Hostname of the VM container
		:return: True if disk is cleaned, otherwise false
		"""
		result = re.search("file:([^,]+)", disk_spec)
		disk = result.group(1)
		print "  Removing disk %s from node %s" % (disk, host)
		(out, exitcode) = pragma.utils.getOutputAsList(
			"ssh %s rm -f %s" % (host, disk))
		if exitcode != 0:
			sys.stderr.write("Problem removing disk %s: %s\n" % (
				host, "\n".join(out)))
			return False
		return True

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
