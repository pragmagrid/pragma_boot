import abc
import cookielib
import datetime
import logging
import os
import pragma.repository.http
import pragma.utils
import re
import string
import time
import urllib2
import xml.etree.ElementTree as ET


class Repository(pragma.repository.http.Repository):
	DOWNLOAD_CHUNK_SIZE = 250 * 1024 * 1024

	def __init__(self, settings):
		"""
		Create a new clonezilla remote repository

		:param settings: Config file settings
		"""
		super(Repository, self).__init__(settings)

		self.type = "clonezilla"
		self.logger = logging.getLogger(self.__module__)
		self.unique_id = "%s-%d" % (time.strftime('%Y%m%d'), os.getpid())
		self.cziso = None
		self.local_image_url = None
		self.include_images = None
		self.exclude_images = None

		self.checkSettings()
		self.checkVcdbFile()

	def checkSettings(self):
		"""
		Read settings from config file

		"""
		super(Repository, self).checkSettings()
		msg = "Check repository_settings{} in configuration file"
		if 'cziso' not in self.settings:
			self.abort("%s. Missing 'cziso' setting." % msg)
		self.cziso = self.settings['cziso']
		if 'local_image_url' not in self.settings:
			self.abort("%s. Missing 'local_image_url' setting." % msg)
		self.local_image_url = self.settings['local_image_url']
		if 'include_images' in self.settings:
			self.include_images = re.compile(self.settings['include_images'])
		if 'exclude_images' in self.settings:
			self.exclude_images = re.compile(self.settings['exclude_images'])

	def checkVcdbFile(self):
		""" Read virtual cluster database if exists """
		self.vcdbFile = self.getLocalFilePath(self.vcdbFilename)
		if os.path.isfile(self.vcdbFile):
			self.readVcdb()

	def downloadImage(self, vcname):
		""" Don't download images """
		pass

	def listRemoteRepository(self):
		"""
		Read the Google drive remote repository.  Each folder in the
		specified Google drive directory is attempted to be read as a
		virtual cluster.

		:return: An array containing remote virtual clusters
		"""
		self.logger.debug("Listing remote repository %s" % self.repository_url)
		repo_items = GdriveObject.listFolder(self.repository_url)
		if not repo_items:
			self.abort("Remote repository is empty")
		virtual_clusters = []
		for repo_item in repo_items:
			if repo_item.type == 'application/vnd.google-apps.folder':
				if self.include_images is not None:
					if not self.include_images.match(repo_item.name):
						self.logger.debug("Remote virtual cluster %s does not match includes_images regex; ignoring" % repo_item.name)
						continue
				if self.exclude_images is not None:
					if self.exclude_images.match(repo_item.name):
						self.logger.debug(
							"Remote virtual cluster %s matches excludes_images regex; ignoring" % repo_item.name)
						continue
				vc = CzisoVirtualCluster(self.getLocalFilePath(repo_item.name))
				if vc.readFromGdrive(repo_item.id, repo_item.name):
					virtual_clusters.append(vc)
		return virtual_clusters

	def sync(self):
		"""
		Sync the remote virtual clusters to local disk
		"""
		remote_vcs = self.listRemoteRepository()
		self.checkVcdbFile()
		for vc in remote_vcs:
			self.logger.info("Syncing virtual cluster %s" % vc.name)
			vc_path = os.path.join(self.repo, vc.name)
			self.logger.info(
				"  Checking virtual cluster %s in remote repository" % vc.name)
			vc.sync(vc_path)
			self.logger.info("  Syncing %s virtual cluster to local format" % vc.name)
			vc_xml = vc.convertToLocal(self.cziso, self.local_image_url)
			self.vcdb[vc.name] = vc_xml
		self.writeVcdb()

class GdriveObject:
	"""
	Object to handle syncing of file in between Google drive and local disk
	"""
	def __init__(self, id, name, type, last_modified):
		self.id = id
		self.name = name
		self.type = type
		self.last_modified = last_modified
		self.local_file = None
		self.logger = logging.getLogger(self.__module__)

	def download(self):
		"""
		Download a file from Google drive

		:return: True if downloaded and False if not
		"""
		url = "https://docs.google.com/uc?id=%s&export=download" % self.id

		# get cookie and confirm code
		self.logger.debug("Getting cookie for file %s at %s" % (self.id, url))
		cookie_support = urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar())
		opener = urllib2.build_opener(cookie_support, urllib2.HTTPHandler)
		urllib2.install_opener(opener)
		response = opener.open(url)
		response_str = response.read()
		matcher = re.search("confirm=(\w+)", response_str)
		if matcher is not None:
			confirm_code = matcher.group(1)
			# download to file
			download_url = "%s&confirm=%s" % (url, confirm_code)
			self.logger.debug("Download url is %s" % download_url)
			self.logger.info("Downloading file %s to %s" % (
				self.name, self.local_file))
			response = opener.open(download_url)
			f = open(self.local_file, "wb")
			data_downloaded = 0
			while True:
				data = response.read(Repository.DOWNLOAD_CHUNK_SIZE)
				if data:
					f.write(data)
					data_downloaded += len(data)
					self.logger.debug("File %s downloading: %i MB so far" % (
						self.name, int(data_downloaded/(1024*1024))))
				else:
					self.logger.debug("File %s download complete!" % self.name)
					break
		else:
			# for small files
			with open(self.local_file, "w") as f:
				f.write(response_str)

		# Do some file checking
		self.logger.debug("%s size = %i" % (
			self.local_file, os.path.getsize(self.local_file)))
		if os.path.getsize(self.local_file) < 5:
			return False
		return True

	def get_local_file(self):
		"""
		Get the local filename of the filename object

		:return: A string containing the path for local file
		"""
		return self.local_file

	@staticmethod
	def listFolder(id):
		"""
		List the contents of a Google drive folder

		:param id: A string containing the id of a Google drive folder

		:return: An array of Gobjects
		"""
		html = None
		url = "https://drive.google.com/drive/u/1/folders/%s" % id
		try:
			response = urllib2.urlopen(url)
			html = response.read()
		except Exception as e:
			self.logger.error("Unable to read remote repository: %s" % str(e))
			return []
		# need to parse javascript html for listing.
		# string beginning with <script>window['_DRIVE_ivd'] contains data
		# first remove some special chars: \x22 and \x5[a-z]
		html = re.sub("\\\\x22", "", html)
		html = re.sub("\\\\x5[a-z]", "", html) 
		html = re.sub("\\\\n", "", html) 
		# then find occurrences of gid,pid,name,obj_type,0,0,0,0,0,created,modified
		file_info = re.findall(
			"(\w{28}),\w{28},([^,]+),([^,]+)(?:,0){5},\d+,(\d+)", html)
		gobjects = []
		for (gid, name, obj_type, modified) in file_info:
			obj_type = obj_type.replace("\/", "/")
			modified_date = int(modified) / 1000
			gobjects.append(GdriveObject(gid, name, obj_type, modified_date))
		return gobjects

	def set_local_file(self, file):
		"""
		Set the path to the local file for this Google file

		:param file: A string containing the path to the local file
		"""
		self.local_file = file

	def sync(self):
		"""
		Sync the file to local disk if updated.

		:return: True if file was synced and False if already synced
		"""
		if not os.path.exists(self.get_local_file()):
			self.download()
			return True
		local_file_age = os.path.getmtime(self.get_local_file())
		self.logger.debug("    %s age = %i" % (self.name, self.last_modified))
		self.logger.debug("    %s age = %i" % (self.get_local_file(), os.path.getmtime(self.get_local_file())))
		if self.last_modified > local_file_age:
			self.logger.info("    Newer version of %s found" % self.name)
			self.download()
			return True
		self.logger.info("    %s already up to date" % self.get_local_file())
		return False


class CzisoVirtualCluster:
	"""
	Represents a virtual cluster in Clonezilla ISO format
	"""
	def __init__(self, repo_path):
		self.name = None
		self.xml = None
		self.compute = None
		self.frontend = None
		self.repo_path = repo_path
		self.logger = logging.getLogger(self.__module__)

	def convertToLocal(self, cziso, local_image_url):
		"""
		Convert a Clonezilla ISO virtual cluster to a local virtual cluster
		in specified local format

		:param cziso: The path to the cziso tool
		:param local_image_url: A URL indicating the format of the local images

		:return: The XML file of the converted local virtual cluster
		"""
		compute = None
		if self.compute:
			compute = CzisoImage.create(cziso, local_image_url, self.compute.get_local_file())
		frontend = CzisoImage.create(cziso, local_image_url, self.frontend.get_local_file())
		if (self.compute and compute is None) or frontend is None:
			self.logger.error("Unknown image type %s" % local_image_url)
			return
		local_xml_file = LocalLibvirtXml(self.xml.get_local_file(), frontend, compute)
		local_xml_file.sync()
		if (self.compute is None or compute.sync()) | frontend.sync():
			local_xml_file.write_local()
		return local_xml_file.file

	def readFromGdrive(self, id, name):
		"""
		Read the virtual cluster from Google drive, a XML file and cziso files
		for a frontend and compute.

		:param id: A string containing the id of the Google drive

		:param name: The name of the virtual cluster

		:return: True if all parts of virtual cluster exists and False if not
		"""
		self.name = name
		vc_items = GdriveObject.listFolder(id)
		for vc_item in vc_items:
			vc_item.set_local_file(os.path.join(self.repo_path, vc_item.name))
			if re.search(".xml", vc_item.name):
				self.xml = vc_item
			if re.search("compute", vc_item.name):
				self.compute = vc_item
			if re.search("frontend", vc_item.name):
				self.frontend = vc_item
		if self.xml is None:
			self.logger.error("No XML found in Google driver folder %s" % name)
			return False
		if self.frontend is None:
			self.logger.error(
				"No frontend iso found in Google driver folder %s" % name)
			return False
		return True

	def sync(self, repo_path):
		synced = False
		if not os.path.exists(repo_path):
			os.makedirs(repo_path)
		vc = [self.xml, self.frontend]
		if self.compute is not None:
			vc.append(self.compute)
		for gobject in vc:
			if gobject.sync():
				synced = True
		return synced

class CzisoImage:
	"""
	Used to manage sync between a local Clonezilla ISO and it's locally
	formatted image.
	"""
	def __init__(self, cziso, local_image_url, cziso_file):
		self.cziso = cziso
		self.local_image_url = local_image_url
		self.cziso_file = cziso_file
		self.image_name = re.split("\.", os.path.split(cziso_file)[1])[0]
		self.repo_dir = os.path.split(cziso_file)[0]
		local_url_template = string.Template(self.local_image_url)
		self.local_url = local_url_template.substitute(
			imagename=self.image_name, repository_dir=self.repo_dir)
		self.logger = logging.getLogger(self.__module__)

	@staticmethod
	def create(cziso, local_image_url, cziso_file):
		"""
		Create a locally formatted specific subclass instance of this class
		that knows when to sync

		:param cziso:  A string containing the path the cziso executable
		:param local_image_url: A string containing the URL representing the
		local image format to use (e.g., zvol, raw, or qcow2)
		:param cziso_file: A string containing the path to the cziso file

		:return: A subclass of CzisoImage or None if local_image_url format
		 not recognized
		"""
		logger = logging.getLogger(CzisoImage.__module__)
		# do a quick check on the ISO file
		(out, rc) = pragma.utils.getOutputAsList("file %s" % cziso_file)
		if rc != 0:
			logger.error("Error running file on %s: %s" % (
				cziso_file, "\n".join(out)))
			return None
		if not re.search("ISO 9660 CD-ROM", out[0]):
			logger.error("File type '%s' not right for %s" % (
				out[0], cziso_file))
			try:
				os.remove(cziso_file)
				logger.info("Removed bad file %s so download can be re-tried next time this is run" % cziso_file)
			except Exception as e:
				logger.error("Error removing bad file %s: %s" % (cziso_file, str(e)))
			return None
		logger.debug("ISO file %s looks good %s" % (out[0], cziso_file))

		image_type = re.split(":", local_image_url)[0]
		if image_type == 'zfs':
			return CzisoImageZfs(cziso, local_image_url, cziso_file)
		if image_type == 'file':
				return CzisoImageFile(cziso, local_image_url, cziso_file)
		else:
			return None

	@abc.abstractmethod
	def get_mtime(self):
		"""
		Get the last modified time of the local image.

		:return: An integer representing the last modified time in secs
		"""
		pass

	def sync(self):
		"""
		Check to see if the local image is out of date from the cziso file.
		If it is, resync the files.

		:return:  True if sync was necessary; otherwise False if already up
		to date
		"""
		self.logger.debug("    %s age = %i" % (
			self.cziso_file, os.path.getmtime(self.cziso_file)))
		self.logger.debug(
			"    %s age = %i" % (self.local_url, self.get_mtime()))
		if self.get_mtime() < os.path.getmtime(self.cziso_file):
			self.logger.info("    Newer version of %s found" % self.cziso_file)
			cmd = "%s restore %s %s overwrite=true >& %s" % (
				self.cziso, self.cziso_file, self.local_url,
				os.path.join(self.repo_dir, "%s-restore.log" % self.image_name))
			self.logger.info(cmd)
			rc = os.system(cmd)
			return rc == 0
		else:
			self.logger.info("    %s already up to date" % self.local_url)
			return False


class CzisoImageZfs(CzisoImage):
	"""
	Used to manage sync between a local Clonezilla ISO and ZFS volume
	"""
	def __init__(self, cziso, local_image_url, image_name):
		CzisoImage.__init__(self, cziso, local_image_url, image_name)
		matcher = re.match("zfs://([^\/]+)/([^\/]+)/", local_image_url)
		if matcher is None:
			raise ValueError("Unable to parse zfs url %s" % local_image_url)
		self.nas = matcher.group(1)
		self.pool = matcher.group(2)
		self.volume = "%s-vol" % self.image_name

	def get_mtime(self):
		"""
		Get the last modified time of the local image.

		:return: An integer representing the last modified time in secs or 0
		if file does not exist
		"""
		(out, rc) = pragma.utils.getOutput(
			"ssh %s zfs get creation %s/%s" % (self.nas, self.pool, self.volume)
		)
		if rc != 0:
			return 0
		matcher = re.search("(\w+\s+\w+\s+\d+\s+\d+:\d+\s+\d+)", out)
		if matcher is not None:
			creation_time_string = matcher.group(1)
			creation_time = datetime.datetime.strptime(creation_time_string, "%a %b  %d %H:%M %Y")
			# adding a minute onto age since granularity of ZFS vol is only mins
			# better to round up than down
			return time.mktime(creation_time.timetuple()) + 60
		return 0

	def setLibvirtDisk(self, libvirtxml, xpath):
		"""
		Set the libvirt disk description based on the local format

		:param libvirtxml: The root of a XML document representing a libvirt
		file
		:param xpath: The path to the disk in libvirtxml to replace

		:return: True if disk successfully replaced and False otherwise
		"""
		disk = libvirtxml.find(xpath)
		if disk is None:
			self.logger.error("Unable to find frontend disk in xml spec")
			return False
		disk.attrib = {'type': 'volume', 'device': 'disk'}
		ET.SubElement(
			disk,
			'source',
			attrib={'volume': self.volume, 'pool': self.pool, 'host': self.nas})
		ET.SubElement(disk, 'target', attrib={'dev': 'vda', 'bus': 'virtio'})
		return True


class CzisoImageFile(CzisoImage):
	"""
	Used to manage sync between a local Clonezilla ISO and local file
	"""
	def __init__(self, cziso, local_image_url, image_name):
		CzisoImage.__init__(self, cziso, local_image_url, image_name)
		self.local_file = self.local_url.replace("file://", "")

	def get_mtime(self):
		"""
		Get the last modified time of the local image.

		:return: An integer representing the last modified time in secs or 0
		if file does not exist
		"""
		if os.path.exists(self.local_file):
			return os.path.getmtime(self.local_file)
		else:
			return 0

	def setLibvirtDisk(self, root, xpath):
		"""
		Set the libvirt disk description based on the local format

		:param libvirtxml: The root of a XML document representing a libvirt
		file
		:param xpath: The path to the disk in libvirtxml to replace

		:return: True if disk successfully replaced and False otherwise
		"""
		disk = root.find(xpath)
		if disk is None:
			self.logger.error("Unable to find frontend disk in xml spec")
			return
		disk.attrib = {'type': 'file', 'device': 'disk'}
		ET.SubElement(
			disk,
			'source',
			attrib={'file': os.path.split(self.local_file)[1]})
		ET.SubElement(disk, 'target', attrib={'dev': 'vda', 'bus': 'virtio'})


class LocalLibvirtXml:
	"""
	Handle manipulation of disk generic libvirt xml file to local formats
	"""
	def __init__(self, remote_xml, frontend, compute):
		self.remote_file = remote_xml
		self.file = remote_xml.replace(".xml", "-local.xml")
		self.frontend = frontend
		self.compute = compute
		self.logger = logging.getLogger(self.__module__)

	def sync(self):
		"""
		Sync the disk expanded libvirt file if the generic is newer

		:return:
		"""
		if not os.path.exists(self.file):
			self.write_local()
		if os.path.getmtime(self.remote_file) > os.path.getmtime(self.file):
			self.write_local()

	def write_local(self):
		"""
		Write the expanded libvirt file to disk
		"""
		local_xml = ET.parse(self.remote_file)
		self.frontend.setLibvirtDisk(local_xml, "//frontend//disk")
		if self.compute:
			self.compute.setLibvirtDisk(local_xml, "//compute//disk")
		self.logger.info("Writing local xml file to %s" % self.file)
		local_xml.write(self.file)
