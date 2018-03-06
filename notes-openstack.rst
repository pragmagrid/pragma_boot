OpenStack driver notes
=========================

Notes about requirements and driver for the OpenStack
Links to the documentation


Official OpenStack Documentation
---------------------------------

Links to the most useful OpenStack user and developer guides 

#. OpenStack Project `User Guides`_

#. See `Image requirements`_ for a list of Linux-based image
   requirements

#. List of current API verisons  `OpenStack API Documentation`_

#. Using OpenStack SDK is one of the methods of sending API requests.
   Python module **openstack**  must be installed on the host that sends API requests. 
   A guide to the usage is `Getting started with OpenSTack SDK`_
   From there see links to all other User Guides. For example, 
   * `Connect`_ - create a conenciton with credentials
   * `Using OpenStack Compute`_ - list iamges, servers, flavors, networks; create server...

#.  Python bindings to the `OpenStack nova API`_
    A python API and a CLI script **nova**. Each implements OpenStack Nova API. 
	A Python `novaclient API`_ needs python modules **novaclient** and **keystoneauth**

#. Python bindings to the OpenStack Identiy API `python keystone`_

#. OpenStack Pike Project `User Guides`_  and `Admin guides`_

.. _Admin guides : https://docs.openstack.org/pike/admin/
.. _User Guides : https://docs.openstack.org/pike/user/ 
.. _Image requirements: https://docs.openstack.org/image-guide/openstack-images.html
.. _User Guides: https://docs.openstack.org/user/
.. _python keystone: https://docs.openstack.org/python-keystoneclient/latest/index.html
.. _novaclient API: https://docs.openstack.org/python-novaclient/latest/reference/api/index.html
.. _OpenStack Nova API: https://docs.openstack.org/python-novaclient/latest/index.html
.. _Using OpenStack Compute: https://developer.openstack.org/sdks/python/openstacksdk/users/guides/compute.html
.. _Connect: https://developer.openstack.org/sdks/python/openstacksdk/users/guides/connect.html
.. _OpenStack API Documentation: https://developer.openstack.org/api-guide/quick-start/
.. _Getting started with OpenSTack SDK: https://developer.openstack.org/sdks/python/openstacksdk/users/index.html

