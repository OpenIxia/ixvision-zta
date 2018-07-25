#!/usr/bin/env python

#################################################################################
##
## File:   get_nto_config.py
## Date:   March 7, 2017
## Author: Fred Mota (fmota@ixiacom.com)
##
## History:
##
## Description:
## This script gets and saves in a text file the configuration (all the details)
## of each port, port group and filter on an NTO.
##
## This is useful when downgrading the version on a NTO, since it is not possible
## to import configuration genearted by a newer release into an older release.
##
## (c) 1998-2017 Ixia. All rights reserved.
##
##############################################################################

import sys
import getopt
import threading
import json
from ixia_nto import *

def getConfig(host_ip, port, username, password, keyword):

    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port)

    config = {}

    for object in nto.searchPorts({"keywords":[keyword]}):
        details = nto.getPort(str(object['id']))
        config[object['id']] = {'name': details['default_name'], 'type': 'port', 'details': details}

    for object in nto.getAllAfms():
        details = nto.getAfm(str(object['id']))
        config[object['id']] = {'name': details['default_name'], 'type': 'afm', 'details': details}

    f = open(host_ip + '_config.txt', 'w')
    f.write(json.dumps(config))
    f.close()

argv = sys.argv[1:]
username = ''
password = ''
keyword = ''
host = ''
hosts_file = ''
config_file = ''
port = 8000

try:
    opts, args = getopt.getopt(argv,"u:p:k:h:f:r:", ["username=", "password=", "keyword=", "host=", "hosts_file=", "port="])
except getopt.GetoptError:
    print 'get_nto_config.py -u <username> -p <password> -k <keyword> [-h <hosts> | -f <host_file>] [-r port]'
    sys.exit(2)
for opt, arg in opts:
    if opt in ("-u", "--username"):
        username = arg
    elif opt in ("-p", "--password"):
        password = arg
    elif opt in ("-k", "--keyword"):
        keyword = arg
    elif opt in ("-h", "--host"):
        host = arg
    elif opt in ("-f", "--hosts_file"):
        hosts_file = arg
    elif opt in ("-r", "--port"):
        port = arg

if username == '':
    print 'get_nto_config.py -u <username> -p <password> -k <keyword> [-h <hosts> | -f <host_file>] [-r port]'
    sys.exit(2)

if password == '':
    print 'get_nto_config.py -u <username> -p <password> -k <keyword> [-h <hosts> | -f <host_file>] [-r port]'
    sys.exit(2)

if keyword == '':
    print 'get_nto_config.py -u <username> -p <password> -k <keyword> [-h <hosts> | -f <host_file>] [-r port]'
    sys.exit(2)

if (host == '') and (hosts_file == ''):
    print 'get_nto_config.py -u <username> -p <password> -k <keyword> [-h <hosts> | -f <host_file>] [-r port]'
    sys.exit(2)

hosts_list = []
if (hosts_file != ''):
    f = open(hosts_file, 'r')
    for line in f:
        line = line.strip()
        if (line != '') and (line[0] != '#'):
            hosts_list.append(line.split(' '))
    f.close()
else:
    hosts_list.append([host, host])

threads_list = []
for host in hosts_list:
    host_ip = host[0]
    
    thread = threading.Thread(name=host, target=getConfig, args=(host_ip, port, username, password, keyword))
    threads_list.append(thread)

for thread in threads_list:
    thread.daemon = True
    thread.start()

try:
    while threading.active_count() > 1:
        for thread in threads_list:
            thread.join(1)
        sys.stdout.write('.')
        sys.stdout.flush()
except KeyboardInterrupt:
    print "Ctrl-c received! Sending kill to threads..."
    sys.exit()
print ""
