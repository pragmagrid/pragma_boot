#!/bin/bash
#
# LC

image=bioapp5-zhengc.img

#prepatch virt-v2v
guestmount -a $image -m /dev/sda1 temp/
cp temp/etc/yum.conf yum.backup
cat >> temp/etc/yum.conf << "EOF"
[main]
cachedir=/var/cache/yum
debuglevel=2
logfile=/var/log/yum.log
pkgpolicy=newest
distroverpkg=redhat-release
tolerant=1
exactarch=1
assumeyes=1


[base]
enabled = 1 
name=CentOS-$releasever - Base
mirrorlist=http://mirrorlist.centos.org/?release=$releasever&arch=$basearch&repo=os
#baseurl=http://mirror.centos.org/centos/$releasever/os/$basearch/
EOF
fusermount -u temp
sleep 3

#prepare output.xml
#prepare storage-pool

#converting the kernel
virt-v2v  -f virt-v2v.xml -f /var/lib/virt-v2v/virt-v2v.db -i libvirtxml  -oa sparse -os transferimages output.xml
if [ "$?" != "0" ] ; then echo something happen during virt-v2v; exit -1; fi


# postpatch virt-v2v
guestmount -a $image -m /dev/sda1 temp/
cp yum.backup temp/etc/yum.conf
fusermount -u temp


