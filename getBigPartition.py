#! /opt/rocks/bin/python
#

import os
import pwd
import sys
import string
import rocks.vm
import rocks.commands


    

username = pwd.getpwuid(os.geteuid())[0]
passwd = ''

if username == 'root':
	conf_file = '/root/.rocks.my.cnf'

try:
	file=open(conf_file,'r')
	for line in file.readlines():
		l=string.split(line[:-1],'=')
		if len(l) > 1 and l[0].strip() == "password":
			passwd = l[1].strip()
			break
	file.close()
except:
	pass

try:
	host = rocks.DatabaseHost
except:
	host = 'localhost'

# Now make the connection to the DB

try:
	from MySQLdb import *

	# Connect over UNIX socket if it exists, otherwise go over the
	# network.

	if os.path.exists('/var/opt/rocks/mysql/mysql.sock'):
		Database = connect(db='cluster',
			host='localhost',
			user=username,
			passwd='%s' % passwd,
			unix_socket='/var/opt/rocks/mysql/mysql.sock')
	else:
		Database = connect(db='cluster',
			host='%s' % host,
			user=username,
			passwd='%s' % passwd,
			port=40000)

except ImportError:
	Database = None
except OperationalError:
	Database = None


db = rocks.commands.DatabaseConnection(Database)
vm = rocks.vm.VM(db)
prefix = vm.getLargestPartition(db.getHostname(sys.argv[1]))

print prefix
