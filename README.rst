The pragma_boot script
----------------------

**pragma_boot** is the main program to instantiate Virtual Machine in Pragma.
It accepts the following agruments:

--vcname vcname    the name of the virtual clutster to start up (the name must be in the database)
--base_path path   the base path of the VM database 
--num_compute N    the number of compute node to start up (default to 0)
--net_conf file    a filename containing the network configuration for 
                   the new cluster frontend.


The network configuration file will contains the self explicative elements:

::

 public_ip="123.123.123.123"
 netmask="255.255.255.0"
 gw="123.123.123.1"
 dns="8.8.8.8"
 fqdn="fqdn_of_pubblic_ip.somehost.com"


pragma_boot is divided into several subscripts which will be called by the pragma_boot 
invocation as described below. If the command is called `vc_driver/command_name` pragma_boot
will replace the vc_driver with the value of the element `vc/distro@driver` in the vc-in.xml 
file (each virtual machine will be able to choose its own vc_driver).
If the command starts with ve_driver it will be replaced with the local Virtual Engine (VE) 
driver which can be configured in the file (specify a file)



* **vc_driver/pre_fix_driver** it prepares the current machine for the execution of 
  the fix_driver script which will follow. Input args are:

  * **path** the vm disk path

* **ve_driver/fix_driver** (use virt-v2v) prepare the given VM image to be run 
  on the current system (fix kernel, drivers, boot options, for 
  current platform, etc.). It's input argumets are (in the following order):

  * **path** the vm disk path
  * **eth0,eth1** the interface name

* **vc_driver/post_fix_driver** it restore the machine state (if needed) after the 
  execution of the fix_driver script. t's input argumets are:

  * **path** the vm disk path


* **vc_driver/pre_boot** it takes care of fixing networking and other stuffs, it 
  depends on the source VM type (if UCSD VM run rocks/pre_boot, etc.)
  probably this script should be in the source folder where the VM 
  images are.
  
  * interface1=aa:ff:bb:44:33:22,eth0,137.120.1.24,255.255.255.0
    the parameter of the NIC 1 as they should be configured in the 
    machine
  * gateway=123.123.123.1
  * dns=1.1.1.1

* **ve_driver/boot** it takes care of starting the VM on the local virtualization 
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
   <driver>rocks6_client</driver>
   <frontend>
     <!-- this is the libvirt xml syntax unmodified 
          see: http://libvirt.org -->
     <domain type='kvm'>
       <name>calit2-119-222</name>
       <os>
         <type>hvm</type>
         <boot dev='network'/>
         <boot dev='hd'/>
         <bootmenu enable='yes'/>
       </os>
       <memory>1048576</memory>
       <vcpu>1</vcpu>
       <features>
               <acpi/>
               <apic/>
               <pae/>
       </features>
       <devices>
         <emulator>/usr/libexec/qemu-kvm</emulator>
         <interface type='direct'>
           <source dev='eth0.2' mode='bridge'/>
           <mac address='7a:77:6e:40:00:07'/>
           <model type='virtio' />
         </interface>
         <interface type='bridge'>
           <source bridge='eth1'/>
           <mac address='7a:77:6e:40:00:08'/>
           <model type='virtio' />
         </interface>
         <disk type='file' device='disk'>
           <driver name='qemu' type='raw'/>
           <source file='calit2-119-222.img.gz'/>
           <target dev='hda' bus='ide'/>
         </disk>
         <graphics type='vnc' port='-1'/>
         <console tty='/dev/pts/0'/>
       </devices>
     </domain>
     <!-- end libvirt xml format -->
   </frontend>
   <compute memory='1048576' vcpu='1'>
     <boot_dependency parent='frontend'>
       <wait type='clock' value='300'/>
     </boot_dependency>
     <!-- this is the libvirt xml syntax unmodified 
          see: http://libvirt.org -->
     <domain type='kvm'>
       <name>compute-0-0-0</name>
       <os>
         <type>hvm</type>
         <boot dev='network'/>
         <boot dev='hd'/>
         <bootmenu enable='yes'/>
       </os>
       <memory>1048576</memory>
       <vcpu>1</vcpu>
       <features>
         <acpi/>
         <apic/>
         <pae/>
       </features>
       <devices>
         <emulator>/usr/libexec/qemu-kvm</emulator>
         <interface type='direct'>
           <source bridge='eth0.2'/>
           <mac address='7a:77:6e:40:00:0a'/>
           <model type='virtio' />
         </interface>
         <disk type='file' device='disk'>
           <driver name='qemu' type='raw'/>
           <source file='hosted-vm-0-0-1.img.gz'/>
           <target dev='hda' bus='ide'/>
         </disk>
         <graphics type='vnc' port='-1'/>
         <console tty='/dev/pts/0'/>
       </devices>
     </domain>
     <!-- end libvirt xml format -->
   </compute>
   <networks>
     <network name='private'>
       <ipaddress>10.1.1.1</ipaddress>
       <netmask>255.255.0.0</netmask>
     </network>
     <frontend>
         <public>eth1</public>
     </frontend>
   </networks>
 </vc>


vc-out.xml file example


::

 <vc type='Local Beowulf'>
   <virtualization engine='kvm' type='hvm' arch='x86_64'/>
   <frontend name='calit2-119-225' fqdn='calit2-119-225.ucsd.edu' ip='137.110.119.225'/>
   <!-- should we allow changing the FE mac address -->
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

