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

#. Install libguestfs-tools-c package on frontend node only ::

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

   **Note:**  If you are using kvm_rocks and want to host all/some if the latest PRAGMA virtual cluster images, the easiest setup will be to configure site_conf.conf to use the "clonezilla" repository type.  Please see the `clonezilla`_ section below for more information.
   
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

**pragma** currently supports 4 repository classes that are configured in the 
``<install-dir>/etc/site_conf.conf`` file. This file has a python syntax and 
specifies settings for the physical site configuration. 

local
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Virtual images are stored on the local disk.  The following parameters are required:

* **repository_class** - should be set to "local".

* **repository_dir** - a path to a directory containing a virtual cluster database file (vcdb.txt) and 
  subdirectories for virtual cluster images. Each subdirectory contains  1 or 2
  images (only frontend, or frontend and compute) and a xml file (lbivirt style) that describes images.

* **vcdb_filename** - the name of the virtual cluster database file.  It is assumed to be relative to 
  the repository_dir param above.  The format of the vcdb.txt file is::

      virtualClusterX,/path/to/XmlDescription/virtualClusterX.xml
      virtualClusterY,/path/to/XmlDescription/virtualClusterY.xml

  For example, contents of the file describing images for 3 virtual clusters : ::

      airbox,/state/kvmdisks/repository/airbox/airbox.xml
      centos7,/state/kvmdisks/repository/centos7/centos7.xml
      rocks-basic,/state/kvmdisks/repository/rocks-basic/rocks-basic.xml

  If raw or qcow2 file images are stored in the repository, their locations are assumed to be 
  in the same relative directory as the libvirt xml description of the virtual cluster.  
  Therefore we recommend the following sub-directory structure for the
  repository_dir which corresponds to the example vcdb.txt  listed above: ::

      vcdb.txt
      airbox/
        airbox.xml
        airbox.raw
      centos7/
        centos7.xml
        centos7-compute.img
        centos7-frontend.img
      rocks-basic/
        rocks-basic.xml
        rocks-basic-compute.raw
        rocks-basic-frontend.raw
      
http
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Virtual images are hosted on any http/https server including Amazon S3. No authentication is supported.  The following parameters are required:

* **repository_class** - should be set to ``http``.

* **repository_dir** - a path to a directory where the vdcb and images can be cached

* **vcdb_filename** - the name of the virtual cluster database file. See description in `local`_. 

* **repository_url** - base url of the http repository. For Amazon S3, the url is https://s3.amazonaws.com/bucket_name.  
  Note that for Amazon S3, the file must be publicly accessible. Do not omit ``http://`` or ``https://``

clonezilla
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The Clonezilla repository type is a remote repository similar to `http`_ except that the virtual cluster images are stored in a 
generic Clonezilla image format and can then be converted to any image type appropriate to your local installation 
(e.g., zvol, raw, qcow2) using the `Clonezilla tool <http://clonezilla.org/>`_.  The default remote clonezilla 
repository can be found in `Google Drive <https://drive.google.com/drive/u/0/folders/0B3cw7uKWQ3fXcmdfRHBCTV9KaUU>`_.

To use the Clonezilla repository, the following dependencies must be installed:

* `cziso <https://github.com/pragmagrid/cziso>`_

The following parameters are required in site_conf.conf:

* **repository_class** - should be set to "clonezilla".

* **repository_dir** - a path to a directory where the vdcb and images can be cached

* **vcdb_filename** - the name of the virtual cluster database file. See description in `local`_. 

* **repository_url** - base url of the Clonezilla repository in Google drive.  Please use the default value specified in the site_conf.conf file.

* **cziso** - full path to the cziso tool installed on this system.

* **local_image_url** - a cziso URL template indicating the desired image format for your local installation (e.g., zvol, raw, qcow2).
  The value $repository_dir will be replaced by the value specified above and $imagename will be replaced by the virtual cluster image
  name found in the Clonezilla repository.  Examples of valid local_image_urls are found below: 

  * for ZFS volume on rocks cluster: ``zfs://nas-0-0/pragma/$imagename-vol``
  * for RAW images: ``file://$repository_dir/$imagename.raw`` or ``file://$repository_dir/$imagename.img``
  * for QCOW2 images: ``file://$repository_dir/$imagename.qcow2``

The following parameters are optional for the Clonezilla repository:

* **include_images** - only sync images from remote repository that match a specified pattern. 

* **exclude_images** - sync all images from remote repository except those matching the specified pattern.

This repository type is intended to be synced regularly (e.g., daily or weekly) with the remote repository.  
Create an executable cron script and run it at a freqeuncy you want to run sync. For example, on  CentOS
or Ubuntu it can be ``/etc/cron.daily/pragma-sync.cron`` or ``/etc/cron.weekly/pragma-sync.cron``.
The content of the executable cron script: ::

  #!/bin/bash
  /opt/pragma_boot/bin/pragma sync repository
  

cloudfront
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Virtual images are hosted on Amazon CloudFront with automatic signed url creation.  

To use the cloudfront repository, the following dependencies will need to be installed:

* boto (version 2.25.0 or later)
* rsa (version 3.1.4 or later)

The following parameters are required in site_conf.conf:

* **repository_class** - should be set to "cloudfront".

* **repository_dir** - a path to a directory where the vdcb and images can be cached

* **vcdb_filename** - the name of the virtual cluster database file. See description in `local`_. 

* **repository_url** - CloudFront ``domain name`` of the distribution to use. Can be found on AWS CloudFront Console. 
  NOTE: Do not omit ``http://`` or ``https://``

* **keypair_id** - CloudFront Key Pair. Generated from AWS Security Console. 

* **private_key_file** : Full path to private key file corresponding to keypair_id. Generated from AWS Security Console. 

To generate a CloudFront Key Pair: 

#. Log into AWS Console
#. Click on account name and select ``Security Credentials``
#. Expand ``CloudFront Key Pairs`` section and click ``Create New Key Pair``
#. Download public key, private key and take note of access key id (keypair_id)

Available Virtual Cluster Images
==============
The following is a description of our available virtual cluster images:

biolinux
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Virtual cluster image based on `Bio-Linux <http://environmentalomics.org/bio-linux/`_, a bioinformatics workstation platform that adds more than 250 bioinformatics packages to an Ubuntu Linux 14.04 LTS base, providing around 50 graphical applications and several hundred command line tools. The Galaxy environment for browser-based data analysis and workflow construction is also incorporated.

* **OS**: Ubuntu 14.04
* **Disk Size**: ??
* **Available Formats**: `cziso <https://drive.google.com/open?id=0B3cw7uKWQ3fXdHdLdV81YTBWQmM>`_, `raw <https://drive.google.com/open?id=0B3cw7uKWQ3fXTDgtcmc1NlYzUm8>`_

centos7
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A basic CentOS 7 image.  The compute image is setup with a NAT to the frontend for public connnectivity. 

* **OS**: CentOS 7
* **Disk size**: 100 GB
* **Available Formats**: `cziso <https://drive.google.com/open?id=0B3cw7uKWQ3fXQVdXSnUyVkRhNEE>`_, `raw <https://drive.google.com/open?id=0B3cw7uKWQ3fXMHRnX3VsUzhhclU>`_

grapler
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Virtual cluster image that provides GRAPLEr, an R-based open-source software that brings the power of distributed computing to the fingertips of lake ecology modelers.

* **OS**: CentOS 7
* **Disk size**: 100 GB
* **Available Formats**: `cziso <https://drive.google.com/open?id=0B3cw7uKWQ3fXaF9OQ2ZlM25fczg>`_, `raw <https://drive.google.com/open?id=0B3cw7uKWQ3fXWVNXT1RCOVZZM3c>`_

rocks-sge
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A basic Rocks virtual cluster cluster with the SGE batch scheduler roll.

* **OS**: CentOS 6
* **Disk size**: 100 GB
* **Available Formats**: `cziso <https://drive.google.com/open?id=0B3cw7uKWQ3fXR085amljM09ZTms>`_, `raw <https://drive.google.com/open?id=0B3cw7uKWQ3fXc1NhaC1NNFZvMnM>`_

wa-dock
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Virtual cluster image that provides the `DOCK <http://dock.compbio.ucsf.edu>`_ chemistry software.

* **OS**: CentOS 6
* **Disk size**: 100 GB
* **Available Formats**: `cziso <https://drive.google.com/open?id=0B3cw7uKWQ3fXOTl5ajA0UHBxTk0>`_, `raw <https://drive.google.com/open?id=0B3cw7uKWQ3fXSVd1a1BLTGJOXzg>`_


