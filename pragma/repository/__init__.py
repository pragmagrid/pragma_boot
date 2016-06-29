import xml.etree.ElementTree as ET
import os
import syslog
import logging
import pragma.utils
import subprocess

from shutil import rmtree
from tempfile import mkdtemp
from pragma.repository.processor.fileprocessor import FileProcessor
from pragma.repository.processor.xmlprocessor import XmlInput, XmlOutput


class BaseRepository(object):

    def __init__(self, settings={}):
        super(BaseRepository, self).__init__()
        self.settings = settings
        try:
            self.repo = self.settings["repository_dir"]
        except KeyError:
            self.abort('Check repository_settings{} in configuration file. Missing \"repository_dir\".' )

        # database filename, contains virtual clusters names and their xml files
        try:
            self.vcdbFilename = self.settings["vcdb_filename"]
        except KeyError:
            self.vcdbFilename = 'vcdb.txt' 

        self.vcdbFile   = None # database filename full path
        self.vcdb       = {}   # format {'vcname': '/path/to/cluster.xml', ...}
        self.xmlin      = {}   # format {'vmname': XmlInput object derived from cluster.xml file }
        self.xmlout     = None # XmlOutput object 
        self.stagingDir = None # directory for staging images

	logging.basicConfig()
	self.logger = logging.getLogger(self.__module__)

    def abort(self, msg):
        syslog.syslog(syslog.LOG_ERR, msg)
        raise pragma.utils.CommandError(msg)

    def clean(self):
        """ rm temp files and directories """
        # delete temp stating directory 
        self.rmStagingDir()

    def setStagingDir(self, path):
        """ create a unique temporary directory for staging virtual images """
        if not self.stagingDir:
            self.stagingDir = mkdtemp(suffix=pragma.utils.get_id(), prefix='pragma-', dir=path)

    def rmStagingDir(self):
        """ rm staging directory """
        if os.path.isdir(self.stagingDir):
            rmtree(self.stagingDir)
        
    def createXmlOutputObject(self, path):
        """ create output xml object """
        self.setStagingDir(path)
        self.xmlout = XmlOutput(os.path.join(self.stagingDir, "vc-out.xml"))

    def getXmlOutputObject(self):
        """ return xml output object """
        return self.xmlout

    def listRepository(self):
        """ Returns a sorted array of available virtual images names"""
        return  sorted(self.vcdb.keys())

    def download(self, rpath, lpath):
        """
        Download file from remote path to local path
        Using wget and curl because urllib and urllib2 don't seem to be able
        to complete big file transfers (at least from Google drive)
        """
        # Create directories if neccesary
        local_dir = os.path.dirname(lpath)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # FIXME redo to put all loggin to a single log file for the command
        log = "/tmp/pragma_boot.download.log"

        wget = pragma.utils.which("wget")
        if wget : # using wget 
            subprocess.check_call([wget, "--append-output=%s" % log, "-S", "-O", lpath, rpath])
        else:     # using curl 
            curl = pragma.utils.which("curl")
            if curl is None:
                self.abort ('Cannot find wget or curl for downloading files.')
            subprocess.check_call("%s --retry 5 -L --stderr - -o %s %s 2>&1  1>>%s" % (curl, lpath, rpath, log), shell=True)

        self.logger.info("Downloading %s to %s ... See %s for details" % (rpath, lpath, log))

        if not os.path.isfile(lpath):
            self.abort ('Error downloading %s. See %s for details' % (lpath, log))

    def getLocalFilePath(self, fname):
        """ returns full path to a file in a local repository """
        return os.path.join(self.repo, fname)

    def getRemoteFilePath(self, fname):
        """ returns full path to a file in a remote repository """
        try:
           return os.path.join(self.repository_url, fname)
        except AttributeError:
           self.abort ('Missing repository_url in configuration file.')

    def checkVcdbFile (self):
        """ check if the vcdb file exists, download if needed """
        self.vcdbFile = self.getLocalFilePath(self.vcdbFilename)
        if not os.path.isfile(self.vcdbFile):
            self.logger.warning("Missing %s file. Trying to download from repository url defined in configuration file." % self.vcdbFile)
            rpath = self.getRemoteFilePath(self.vcdbFilename)
            self.download(rpath, self.vcdbFile)

        with open(self.vcdbFile, 'r') as vcdbFile:
            for line in vcdbFile:
                name, path = line.strip().split(',')
                self.vcdb[name] = self.getLocalFilePath(path)

    def getVmXmlTree(self, name):
        """Returns an xmltree object corrsponding to a parsed xml file for a VM 'name'"""
        # download cluster xml description file
        if not os.path.isfile(self.vcdb[name]):
            rpath = self.getRemoteFilePath(os.path.basename(self.vcdb[name]))
            lpath = self.vcdb[name]
            self.download(rpath, lpath)

        return ET.parse(self.vcdb[name])

    def createXmlInputObject(self, name):
        xmlinfo =  self.getVmXmlTree(name)
        dirpath = os.path.dirname(self.vcdb[name])
        self.xmlin[name] = XmlInput(xmlinfo, dirpath)

        arch = self.xmlin[name].getArch()
        if arch != "x86_64":
            self.abort("Unsupported VM architecture '%s' for virtual image %s" % (arch, name))

    def getXmlInputObject(self, name):
        """ returns an xml input object for a VM identified by name """
        return self.xmlin[name]

    def downloadImage(self, vcname):
        """Download all files specified in virtual cluster definition """
        vmXmlObject = self.xmlin[vcname]
        names = vmXmlObject.getImageNames()
        for filename in names:
            rpath = self.getRemoteFilePath(filename)
            lpath = self.getLocalFilePath(os.path.join(vcname, filename))
            if not os.path.isfile(lpath):
                self.download(rpath, lpath)

    def processCluster(self, name, path):

        # check cluster name 
        if name not in self.vcdb:
           self.abort('Virtual image %s does not exist.' % name)

        # check cluster xml description file , download if abcent
        # and create xml input object from it
        self.createXmlInputObject(name)

        # download cluster images
        self.downloadImage(name)

        # process cluster images if needed
        base_dir = os.path.dirname(os.path.join(self.repo, self.vcdb[name]))
        vmXmlObject = self.xmlin[name]

	diskinfo = vmXmlObject.getDiskInfo()
        for node in diskinfo.keys():
            parts = diskinfo[node]['parts']
            type = diskinfo[node]['type']
            file = os.path.join(self.repo,diskinfo[node]['file'])
            fp = FileProcessor(base_dir, file, parts, type)
            fp.process()

        # create xml output object
        self.createXmlOutputObject(path)

        return

    def is_downloaded(self):
        raise NotImplementedError

    def delete_vc(self, vcname):
        """Delete VC from repository cache if exists"""
        raise NotImplementedError

    def clear_cache(self):
        """Clear repository cache entirely"""
        raise NotImplementedError
