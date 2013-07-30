


The pragma_boot script
----------------------


pragma_boot is the main program to instantiate Virtual 
Machine in Pragma. Input:

- VM name 
- base path for VM images
- number of compute (default to 0)
- public IP address

pragma_boot is divided into several subscripts as described below:


* **prepare_machine** (use virt-v2v) prepare the given VM image to be run 
  on the current system (fix kernel, drivers, boot options, for 
  current platform, etc.). It's input argumets are:
  
  * vm_disk_path=path


* **pre_boot** it takes care of fixing networking and other stuffs, it 
  depends on the source VM type (if UCSD VM run rocks/pre_boot, etc.)
  probably this script should be in the source folder where the VM 
  images are.
  
  * interface1=aa:ff:bb:44:33:22,eth0,137.120.1.24,255.255.255.0
    the parameter of the NIC 1 as they should be configured in the 
    machine
  * gateway=123.123.123.1
  * dns=1.1.1.1

* **boot** it takes care of starting the VM on the local virtualization 
  engine. Its input parameters are:
  
  * cpu=3
    number of cpus
  * ram=1024
    Megabytes of RAM
  * vm_disk_path=path  
    the path to it's virtual disks
  * priv_mac_address=aa:ff:bb:44:33:22
    the mac address of the private interface
  * pub_mac_address=aa:ff:bb:44:33:22
    the mac address of the public interface if there is any (this 
    parameters is optionals.

            

input and output XML file example
=================================

           
vc-in.xml file example

::

 <vc type='Local Beowulf'>
   <virtualization engine='kvm' type='hvm' arch='x86_64'/>
   <frontend memory='1048576' vcpu='1'>
     <devices>
       <disk format='raw' bus='virtio'>
         <source file='calit2-119-222.img.gz'/>
       </disk>
       <interface name='eth0'>
         <subnet name='private'/>
         <mac address='7a:77:6e:40:00:07'/>
         <model type='virtio'/>
       </interface>
       <interface name='eth1'>
         <subnet name='public'/>
         <mac address='7a:77:6e:40:00:08'/>
         <model type='virtio'/>
       </interface>
     </devices>
   </frontend>
   <compute memory='1048576' vcpu='1'>
     <boot_dependency parent='frontend'>
       <wait type='clock' value='300'/>
     </boot_dependency>
     <devices>
       <disk format='raw' bus='virtio'>
         <source file='hosted-vm-0-0-1.img.gz'/>
       </disk>
       <interface name='eth0'>
         <subnet name='private'/>
         <mac address='7a:77:6e:40:00:0a'/>
         <model type='virtio'/>
       </interface>
     </devices>
   </compute>
   <networks>
     <network name='private'>
       <ip address='10.1.1.1' netmask='255.255.0.0'/>
     </network>
   </networks>
 </vc>


vc-out.xml file example


::

 <vc type='Local Beowulf'>
   <virtualization engine='kvm' type='hvm' arch='x86_64'/>
   <frontend name='calit2-119-225' fqdn='calit2-119-225.ucsd.edu' ip='137.110.119.225'/>
   <compute count='3'>
     <node name='hosted-vm-0-0' mac='7a:77:6e:40:00:09' ip='10.1.255.254'/>
     <node name='hosted-vm-0-1' mac='7a:77:6e:40:00:0a' ip='10.1.255.253'/>
     <node name='hosted-vm-0-2' mac='7a:77:6e:40:00:0b' ip='10.1.255.252'/>
   </compute>
   <network>
     <dns ip='8.8.8.8' search='local ucsd.edu' domain=''/>
     <gw ip='137.110.119.1'/>
   </network>
 </vc>

