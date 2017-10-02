import logging
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pragma.utils import Abort, ClusterNetwork


class XmlInput:
    def __init__(self, xmltree, dir):
        self.xml = xmltree
        self.dir = dir 
        logging.basicConfig()
        self.logger = logging.getLogger(self.__module__)

        # information about frontend/compute nodes disks
        self.diskinfo = {}

        # set values from xml 
        self.getValues()

    def getValues(self):
        """collect values that will be used for processing"""
        self.setDiskInfo() # collect disk images info

    def getArch(self):
        virt =  self.xml.find("virtualization")
        if virt != None:
            return virt.attrib['arch']
        else:
            self.logger.error("Unable to find virtualization tag")
            return None

    def getImageNames(self):
        """ Returns an array of virtual cluster images file names """
        names = []
        for key in self.diskinfo.keys():
            vals = self.diskinfo[key]
            parts = vals['parts']
            if parts:
                names += parts
            else:
                if 'file' in vals:
                    names.append(vals['file'])
        return names

    def setDiskInfo(self):
        """Parse xml tree info and collect disk-related information for
           frontend and compute nodes. Return it as a dictionary where
           keys are 'frontend', 'compute' if exist, and values are dictionaries
           For example:
           {'type': 'raw', 'name': 'qemu', 'file': 'disk-iamge.img}
        """
        vctree = self.xml.__dict__['_root']  # xml tree object 
        for nodetype in ('frontend', 'compute'):
            diskinfo = {}
            # collect disk info for each nodetype
            node = vctree.find("./%s" % nodetype) # object for frontend or compute 
            try:
                diskinfo.update(node.find(".//disk/driver").attrib) # add keys 'type', 'name'
                diskinfo.update(node.find(".//disk/source").attrib) # add key 'file'
                type,parts = self.getFileType(node)                 # check file type
                if type:
                    diskinfo['type'] = type
                    if not parts:
                        Abort("Error in cluster xml file. Check <part> definition for disk image %s" % diskinfo['file'])
                diskinfo.update({'parts':parts})
                self.diskinfo[nodetype] = diskinfo

            except AttributeError:
                continue

    def getFileType(self, node):
        """ check the virtual image file type and if there are multiple  parts"""
        # check if <file type="ftype"> is present
        ftype = node.find(".//file")
        try: 
            type = ftype.attrib['type']
        except AttributeError:
            type = None

        # collect file parts
        parts = []
        if type:
            partlist = node.findall(".//part")
            for item in partlist:
                parts.append(item.text)

        return type, parts

    def getDiskInfo(self):
        return self.diskinfo
    

    def get_disk(self, node):
        disk = self.xml.find("%s/domain/devices/disk/source" % node)
        if disk != None:
            return disk.attrib
        else:
            self.logger.error("Unable to find disk for node %s" % node)
            return None


class XmlOutput:

    def __init__(self, filename):
        self.filename = filename
        self.compute_filenames = {}
        self.cpus_per_node = {}
        self.network = None
        logging.basicConfig()
        self.logger = logging.getLogger(self.__module__)

    def __str__(self):
        vc = ET.Element('vc')

        frontend = ET.SubElement(vc, 'frontend', attrib={
            'fqdn': self.network.get_fqdn(),
            'name': self.network.get_frontend(),
            'gw': self.network.get_gw(self.network.get_frontend())
        })
        for iface in self.network.get_ifaces('frontend'):
            iface_attrs = self.network.get_net_attrs(iface.network)
            iface_attrs.update(iface.get_attrs())  # local overrides network
            ET.SubElement(frontend, iface.network, attrib=iface_attrs)

        computes = ET.SubElement(vc, 'compute', attrib={
            'count':str(len(self.network.get_computes()))})
        for node in self.network.get_computes():
            compute = ET.SubElement(computes, 'node', attrib={
                'name':self.network.get_node_name(node),
                'cpus':str(self.cpus_per_node[node]),
                'gw': self.network.get_gw(node)})
            for iface in self.network.get_ifaces(node):
                iface_attrs = self.network.get_net_attrs(iface.network)
                iface_attrs.update(iface.get_attrs())  # local overrides network
                ET.SubElement(compute, iface.network, attrib=iface_attrs)
        self.append_network_key(vc)
        return self.prettify(vc)

    def append_network_key(self, vc):
        network = ET.SubElement(vc, 'network')
        ET.SubElement(network, 'dns', attrib = { 
            'ip':self.dns, 'search':"local", 'domain':""})
        key = ET.SubElement(vc, 'key')
        key.text = self.key

    def clean(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        for node in self.compute_filenames:
            if os.path.exists(self.compute_filenames[node]):
                os.remove(self.compute_filenames[node])

    def get_compute_names(self):
        return sorted(self.compute_filenames.keys())

    def get_compute_vc_out(self, node):
        vc = ET.Element('vc')
        ET.SubElement(vc, 'frontend', attrib={
            'fqdn': self.network.get_fqdn()})
        compute = ET.SubElement(vc, 'compute', attrib={
            'name':self.network.get_node_name(node),
            'gw': self.network.get_gw(node)
        })
        for iface in self.network.get_ifaces(node):
            iface_attrs = self.network.get_net_attrs(iface.network)
            iface_attrs.update(iface.get_attrs())  # local overrides network
            ET.SubElement(compute, iface.network, attrib=iface_attrs)
        self.append_network_key(vc)
        return self.prettify(vc)

    def get_frontend(self):
        return self.network.get_frontend()

    def get_kvm_diskdir(self):
        return self.kvm_diskdir 

    def get_vc_out(self, node):
        return self.compute_filenames[node]

    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element.
        """
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def read(self):
        root = ET.parse(self.filename).getroot()

        self.key = root.find("key").text.strip()
        frontend = root.find('frontend')
        self.network = ClusterNetwork(frontend.attrib['name'], frontend.attrib['fqdn'])
        for net in frontend:
            self.network.add_net(net.tag, net.attrib['subnet'], net.attrib['netmask'], net.attrib['mtu'])
            self.network.add_iface(
                self.network.get_frontend(), net.tag, net.attrib['ip'],
                net.attrib['mac'], net.attrib['iface'])
        self.network.add_gw(self.network.get_frontend(), frontend.attrib['gw'])
        compute = root.find('compute')
        dir = os.path.dirname(self.filename)
        for node in compute.getchildren():
            node_name = node.attrib["name"]
            for net in node:
                self.network.add_iface(node_name, net.tag,
                   net.attrib['ip'], net.attrib['mac'], net.attrib['iface'])
            self.network.add_gw(node_name, node.attrib['gw'])
            self.compute_filenames[node_name] = os.path.join(dir, "%s.xml" % node_name)
            self.cpus_per_node[node_name] = node.attrib["cpus"]
        self.dns = root.find("network").find("dns").attrib["ip"]

    def set_frontend(self, name, public_ip, private_ip, fqdn):
        self.frontend = {'name':name, 'public_ip':public_ip, 'private_ip':private_ip, 'fqdn':fqdn}

    def set_key(self, key):
        file = open(key, "r")
        self.key = file.read()
        file.close()
        self.key = self.key.rstrip("\n")

    def set_kvm_diskdir(self, dir):
        self.kvm_diskdir = dir

    def set_network(self, cluster_network, dns):
        self.network = cluster_network
        self.dns = dns
        
    def set_compute_nodes(self, compute_nodes, cpus_per_node):
        dir = os.path.dirname(self.filename)
        for node in compute_nodes:
            self.compute_filenames[node] = os.path.join(dir, "%s.xml" % node)
        self.cpus_per_node = cpus_per_node

    def write_compute(self, node):
        file = open(self.compute_filenames[node], "w")
        file.write(self.get_compute_vc_out(node))
        file.close()
        self.logger.debug("Writing vc-out file to %s" % self.compute_filenames[node])

    def write(self):
        file = open(self.filename, "w")
        file.write(str(self))
        file.close()
        self.logger.debug("Writing vc-out file to %s" % self.filename)
        for node in self.network.get_computes():
            self.write_compute(node)
