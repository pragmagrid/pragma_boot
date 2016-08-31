.. highlight:: rest

The pragma_boot 
----------------------
.. contents::

The pragma_boot script was rewritten in python to accommodate more drivers and
reposittories. The main script is now called **pragma**  and it is used 
to instantiate Virtual Machine in PRAGMA testbed sites.

The agruments to **pragma** depend on the specific command being executed.
The following represents a list of current sub-commands:
 
* **boot** {vc-name} {num-cpus} [enable-ent=boolean] [enable-ipop-client=string] [enable-ipop-server=string] [key=string] [logfile=string] [loglevel=string] 
* **clean** {vc-name} 
* **help** {command} 
* **list cluster** {vc-name} 
* **list help** [subdir=string] 
* **list repository** 
* **shutdown** {vc-name} 

Installation
==============
We recommend install in /opt/pragma_boot

#. Install libguestfs-tools-c package ::

     yum --enablerepo=base install libguestfs-tools-c

#. Check out github repository ::

     cd /opt
     git clone  https://github.com/pragmagrid/pragma_boot

#. Create configuration files for your site  in ``/opt/pragma_boot/etc`` based on site information. 
   The directory contains templates for site configuration file and driver configuration files. 
   For example ::

     cd /opt/pragma_boot/etc 
     cp site_conf.conf.template site_conf.conf  (and edit according to your site info) 
     cp kvm_rocks.conf.template kvm_rocks.conf  (and edit according to your driver info) 
   
   Example site_conf.conf file  for a site using kvm_rocks driver and a local repository::
   
     # Choose is the viritualization engine driver type
     site_ve_driver = "kvm_rocks"

     # Temporary directory for staging virtual images before deployment.
     temp_directory = "/state/partition1/temp"

     # Default directory for log files
     log_directory = "/var/log/pragma_boot"

     # Set individual variables in repositroy_settings based on your site configuration.
     repository_settings = {
        # Required repository class to use
        'repository_class' : "local", 

        # Required local repository directory to use for caching virtual images 
        'repository_dir' : "/state/partition1/vm-images",

        # Optional virtual images database file. Defaults to 'repository_dir'/vcdb.txt 
        'vcdb_filename' : "vcdb.txt",
     }

   Example kvm_rocks.conf file 
   
   The network information in this file is what your physical site can use for the virtual clusters. 
   The IP addresses must have their associated FQDNs and the gateway and DNS info must be current. 
   You need one IP and one vlan per virtual cluster. The example below supports hosting of 2 virtual clusters ::
   
     # public IP addresses pragma_boot can use
     public_ips=["111.110.109.2", "111.110.109.3"]

     # metmask for public IP addresses
     netmask="255.255.255.0"

     # gateway 
     gw="111.110.109.1"

     # DNS server
     dns="8.8.8.8"

     # available vlans that can be used for private network
     vlans= range(22,23)

     # specify alternate directory for images if using NFS; required (leave empty for default)
     diskdir = ""

     # do not allocate all cpus, leave this many empty
     num_processors_reserved = 2

#. Create a local repository directory, the directory path  must correspond to the `repository_dir` in `site_conf.conf` file. 
   For example ::

     mkdir /state/partition1/vm-images 
   
   In this directory create images database file. The default is `vcdb.txt` and it is identified in `site_conf.conf` file
   by `vcdb_name` variable.  Example vcdb.txt file ::
   
      rocks-sge-ipop,rocks-sge-ipop/rocks-sge-ipop.xml
      wa-dock,wa-dock/wa-dock.xml
      hku_biolinux,hku_biolinux/hku_biolinux.xml

   This example file  describes a local repository with 3 virtual clusters. For each  cluster there is a corresponding directory 
   where actual image files and a description xml file are located. For example ::
   
       # ls /state/partition1/vm-images/rocks-sge-ipop/
       nbcr-226-sge-ipop-compute.vda  nbcr-226-sge-ipop-frontend.vda  rocks-sge-ipop.xml

   Create  directories for the images you want to host and download images and their xml files. Email pragma-cloud-admin@googlegroups.com for the download link. 
   
#. Test your configuration. 
   
   Add pragma boot directory to your path ::
   
      # export PATH=$PATH:/opt/pragma_boot/bin
      
   List repositories  ::
  
      # pragma list repository
      VIRTUAL IMAGE
      hku_biolinux
      rocks-sge-ipop
      wa-dock

   The last 4 lines show the expected output for the vcdb.txt example file which lists 3 virtual clusters in the repository
  
  Boot a cluster with a frontend and no compute nodes using hku_biolinux image ::
  
      # pragma boot hku_biolinux 0 loglevel=DEBUG
      
  The log file will be in `/var/log/pragma_boot/`    
          
PRAGMA Virtual Cluster Requirements
==================================
A virtual cluster has a virtual frontend and virtual compute nodes. 
To create a virtual cluster which is compatible with PRAGMA infrastructure the 
nodes must respect the following criteria:

- Physical frontend must have ``fuse`` and ``libguestfs-tools-c`` installed (for a site with kvm_rocks driver)
- All host runs inside kvm-based virtualization engine (for a site with kvm_rocks driver)
- Each VM has a single disk image
- VM disk images can be compressed using Lempel-Ziv coding (with extension .gz)
- VM disk images must be in raw format (no other formats are supported now)
- The first partition on the disk image is the / partition
- No LVM/RAID or other fancy FS type is supported
- Virtual frontend has 2 network interfaces. The first one connects to private
  network, the second connects to public network
- Virtual compute node has 1 network interface connected to a private network
- When the frontend boots, it expects a file in /root/vc-out.xml 
  to configure its network interfaces and the list of compute hosts
- When the compute node boots, it expects a file in /root/vc-out.xml to configure its network

Supported Drivers 
=======================
There are 2 supported drivers represeting site virtualization engine:

#. **cloudstack** - for  CloudStack-enabled site
#. **kvm_rocks** - for Rocks-enabled site.

The following settings must be present in ``<install_path>/etc/site_conf.conf`` file:

* ``site_ve_driver``  - specifies the driver name (one form above list)
* ``temporary_directory`` -  the path for the temporary directory used for
  staging all VM images

For each driver there is a driver configuration file (pytohn syntax) in ``<install_path>/etc/``.
The driver configuration file consists of information that a site
virtualization engine will use for the instantiated virtual images.

1. kvm_rocks configuration file 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* ``public_ips`` - a list of public IP addresses that can be used for virtual clusters. 
* ``netmask`` - metmask for public IP addresses
* ``gw`` - gateway 
* ``dns`` - DNS server
* ``vlans`` - available vlans that can be used for private network, specified as a
  range, for example range(22,25)
* ``diskdir`` - alternate directory for images if using NFS; required (leave empty for default)
* ``available_containers`` - specify vm-containers to use for hostiung virtual
  images (space separated string)
* ``num_processors_reserved`` - do not allocate all cpus, leave this many empty
* ``ent`` - for ENT-enabled sites, specify openvFlow network info
  ::
     ent = {
        'subnet_name': 'openflow',
        'interface_name': 'ovs'
     }

2. cloudstack configuration file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* ``baseurl`` - URL to Cloudstack REST API
* ``apikey`` and ``secretkey``  - Credentials to use Cloudstack REST API
  Go to Accounts -> <your account name> -> View users -> <your username> 
  If "API Key" and "Secret Key" are empty, click the Generate Keys icon (second icon)
* ``templatefilter`` - category of templates where VM instances are configured, for example  "community"
* ``networkoffering`` - Network offering. This is  neded for creating  of new networks for the
  virtual clusters. Theere may be multiple offerings in CloudStack. Default is
  "DefaultIsolatedNetworkOfferingWithSourceNatService"

Supported Repositories
=======================

**pragma** currently supports 3 repository classes which can be configured in site_conf.conf file
which has a python syntax and specifies settings for the physical site configuration. 

* **local** - virtual images are stored on the local disk, cloud repository is * disabled.

* **http** - virtual images are hosted on any http/https server including Amazon S3. No authentication is supported.

  * **repository_url** : required setting, base url of the repository. For Amazon S3, the url is `https://s3.amazonaws.com/<bucket_name>`. 
    Note that for Amazon S3, the file must be publicly accessible. Do not omit http:// or https://

* **cloudfront** - virtual images are hosted on Amazon CloudFront with automatic signed url creation.
  This repository class requires the following settings:

  * **repository_url** : CloudFront `domain name` of the distribution to use. 
    Can be found on AWS CloudFront Console. **Do not omit http:// or https://**
  * **keypair_id** : CloudFront Key Pair. Generated from AWS Security Console. See extras section for instruction.
  * **private_key_file** : full path to private key file corresponded to keypair_id. Generated from AWS Security Console. 
    
  To generate CloudFront Key Pair:

  #. Log into AWS Console
  #. Click on account name and select `Security Credentials`
  #. Expand `CloudFront Key Pairs` section and click `Create New Key Pair`
  #. Download public key, private key and take note of access key id (keypair id)
  
  For using cloudfront repository need to install dependencies:
  
  * boto
  * rsa
