The pragma_boot script
----------------------

**pragma_boot** is the main program to instantiate Virtual Machine in Pragma.
It accepts the following agruments:

* **--num_compute N**    the number of compute node to start up (default to 0)
* **--vcname vcname**    the name of the virtual clutster to start up (the name must be in the database)
* **--base_path path**   the base path of the VM database 



pragma_boot is divided into several subscripts which will be called by the pragma_boot 
invocation as described below. If the command is called `vc_driver/command_name` pragma_boot
will replace the vc_driver with the value of the element `vc/distro@driver` in the vc-in.xml 
file (each virtual machine will be able to choose its own vc_driver).
If the command starts with ve_driver it will be replaced with the local Virtual Engine (VE) 
driver which can be configured in the file (specify a file)


* **ve_driver/allocate** this script takes care of verifying that there are enough 
  resoureces to satisfy the user request, if so it will also allocate public IP, 
  private IPs, MAC addresses, and computing resources. If the system can create 
  SMP nodes it can allocate less compute node with multiple cpus in each node.
  If successful it will write a vc-out.xml file at the location specfied by **vc_out_path** 
  input parameters.

  * **num_compute** it specifies the number of CPU requested by the user. 
  * **vc_out_path** this should point to the path where the vc-out.xml will be saved


* **vc_driver/pre_fix_driver** it prepares the current machine for the execution of 
  the fix_driver script which will follow. Input args are:

  * **path** the vm disk path

* **ve_driver/fix_driver** (use virt-v2v) prepare the given VM image to be run 
  on the current system (fix kernel, drivers, boot options, for 
  current platform, etc.). It's input argumets are (in the following order):

  * **xml_file** the xml file of the virtual machine we have to convert
  * **eth0,eth1** the interface name
  * **temp_directory** the temporary directory used to place all the temporary virtual images

* **vc_driver/post_fix_driver** it restore the machine state (if needed) after the 
  execution of the fix_driver script. t's input argumets are:

  * **path** the vm disk path

* **vc_driver/pre_boot** it takes care of fixing networking and other stuffs, it 
  depends on the source VM type (if UCSD VM run rocks/pre_boot, etc.)
  probably this script should be in the source folder where the VM 
  images are.
  
  * **file_path**   the path where the vm image is
  * **vc_out**      path to the vc-out.xml file
  * **host_name**   the name of the host we want to boot


* **ve_driver/boot** it takes care of starting the VM on the local virtualization 
  engine. Its input parameters are:
  
  * **file_path**   the path where the vm image is
  * **xml_file**    libvirt xml file needed to boot this machine
  * **vc_out**      path to the vc-out.xml file 
  * **host_name**   the name of the host we want to boot



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
         <interface type='bridge'>
           <source bridge='eth0.2'/>
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
   <compute>
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
         <interface type='bridge'>
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

 <vc>
   <frontend>
     <public fqdn="calit2-119-222.ucsd.edu" ip="137.110.119.222" netmask="255.255.255.0" gw="137.110.119.1"/>
     <private ip="10.1.0.0" netmask="255.255.0.0"/>
   </frontend>
   <compute count="2">
     <node name="hosted-vm-0-1-0" mac="7a:77:6e:40:00:15" ip="10.1.0.254"/>
     <node name="hosted-vm-0-0-0" mac="7a:77:6e:40:00:14" ip="10.1.0.253"/>
   </compute>
   <network>
     <dns ip="8.8.8.8" search="local" domain=""/>
   </network>
 </vc>


Questions
=========

* Can the Virtual Cluster choose the private IP addresses as he likes?
  Or it is the hosting environment who completely decides the private IP 
  addressing and range.

* DHCP is it running or not in the hosting evnironment?

