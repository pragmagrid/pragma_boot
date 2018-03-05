
Virtual Images Edits
----------------------
The following is a description of edits for the images/instances.

.. contents::


biolinux  - spectre/meltdown vulenrabilities update
=====================================================
Virtual cluster image based on `Bio-Linux <http://environmentalomics.org/bio-linux/>`_
an Ubuntu Linux 14.04 LTS base.

Original kernel :  ::

    uname -r
	3.13.0-139-generic

This kernel is vulnerable to spectre/meltdown vulnerabilities.
Info on `SpectreAndMeltdown <https://wiki.ubuntu.com/SecurityTeam/KnowledgeBase/SpectreAndMeltdown#Kernel_Mitigations>`_
General Ubuntu `How to do Server Upgrades <https://wiki.ubuntu.com/Security/Upgrades>`_
Use the following steps to update kernel

#. check for updates  

   The number of wrrors/warnings may be different depending on  specific
   Ubuntu version or kernel distro. Here is a sample of possible fixes.  ::

     # apt-get update
     ...
     Fetched 8,860 kB in 26s (333 kB/s)
     Reading package lists... Done

     W: An error occurred during the signature verification. The repository is not
     updated and the previous index files will be used. GPG error:
     http://dl.google.com stable Release: The following signatures couldn't be
     verified because the public key is not available: NO_PUBKEY 1397BC53640DB551
     W: There is no public key available for the following key IDs: 1397BC53640DB551

     W: An error occurred during the signature verification. The repository is not
     updated and the previous index files will be used. GPG error:
     http://www.stats.bris.ac.uk trusty/ Release: The following signatures were
     invalid: KEYEXPIRED 1445181253 KEYEXPIRED 1445181253 KEYEXPIRED 1445181253

     W: Failed to fetch http://dl.google.com/linux/chrome/deb/dists/stable/Release
    
     W: Failed to fetch http://www.stats.bris.ac.uk/R//bin/linux/ubuntu/trusty/Release
    
     W: Failed to fetch http://hk.archive.ubuntu.com/ubuntu/dists/trusty-updates/main/i18n/Translation-en Hash Sum mismatch
     W: Some index files failed to download. They have been ignored, or old ones used instead.
   
   Download public key for google.com (first error above) :: 

     # apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 1397BC53640DB551

   Update expired key (second error above) ::

     # apt-key list | grep expired
     # apt-key adv --recv-keys --keyserver keys.gnupg.net E084DAB9

    Google no longer updates 32 bit chrome, fix for 3rd error :: 

     # vi /etc/apt/sources.list.d/google-chrome.list
    
    Edit line so it looks like the following (add arch) :: 

      deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main

    Fix index files error  with ::

      # rm -vf /var/lib/apt/lists/*

    Rerun **apt-get update**. The endof output chould be similar to ::
      ...
      Ign http://hk.archive.ubuntu.com trusty/universe Translation-en_HK
      Fetched 37.1 MB in 35s (1,048 kB/s)
      Reading package lists... Done

 
#. Do upgrade ::

     # apt-get dist-upgrade
     ...
     159 upgraded, 72 newly installed, 11 to remove and 0 not upgraded.
     Need to get 51.4 MB/427 MB of archives.
     After this operation, 285 MB of additional disk space will be used.
     Do you want to continue? [Y/n]
     
   Type **Y**. May need to answer questions (there are suggestions  Y/N) about specific packages.

   Once finished ::

     # reboot


#. After reboot check for spectre/meltdown vulnerability  ::

     # uname -r 
     3.13.0-142-generic

     # wget https://github.com/speed47/spectre-meltdown-checker/archive/v0.35.tar.gz
     # tar xzvf v0.35.tar.gz
     # cd spectre-meltdown-checker-0.35/
     # ./spectre-meltdown-checker.sh

