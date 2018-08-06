#!/usr/bin/env python
#
# Zero-Touch Provisioning script (playbook) for a Ixia Vision NPB
# Tag ports with keywords matched with LLDP info
# Since this script doesn't change any operational parameters of an NPB, it could be run as often as needed to keep the port tags updated

# 1. Starting point is an Ixia Vision NPB with all required ports enabled and receiving LLDP info from neighbors
# 2. Input parameters to this script enumerate which keywords to look in LLDP Port Description field
# 3. Connect to an NPB and collect LLDP Neighbors info
# 4. Compare LLDP Port Description info with supplied keywords, identify matches
# 5. Tag indentified ports with the matching keywords


import sys
import getopt
import threading
import json
from ixia_nto import *

# DEFINE FUNCTIONS HERE

# Input 
# - Connection to an NPB
# - ZTP scope (how many ports, for example) - we need this for granular control, instead of going through all available ports
# - Keywords to look for

# Model to operate
# NPB
# |_Connection
# |_Type
# |_ZTPScope[PortList]
# |_Keywords[Names]
# |_NeighborList[PortNum,NeighborPortDescription]

def tag_ports(host_ip, port, username, password, tags):

    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port, debug=True, logFile="ixvision_lldp_tag_debug.log")

    neighbor_list = {}

    neighbor_list = nto.getAllNeighbors()
    if len(neighbor_list) == 0:
        return

    for port_name in neighbor_list.keys():
        port = nto.getPortProperties(port_name,'id,keywords')
        for neighbor in neighbor_list[port_name]:
            for tag in tags:
                if tag in neighbor['port_description']:
                    print("Matched port %s with neighbor %s:%s description %s" % (port_name, neighbor['system_name'], neighbor['port_id'], neighbor['port_description']))
                    port_keywords = port['keywords']
                    if port_keywords is None:
                        port_keywords = [tag]
                    else:
                        port_keywords = port_keywords + [tag]
                    nto.modifyPort(str(port['id']), {'keywords': port_keywords})
        

# Main thread

argv = sys.argv[1:]
username = ''
password = ''
tags = []       # A list of keywords to match LLDP info againts
host = ''
hosts_file = ''
config_file = ''
port = 8000

try:
    opts, args = getopt.getopt(argv,"u:p:h:f:r:t:", ["username=", "password=", "host=", "hosts_file=", "port=", "tags="])
except getopt.GetoptError:
    print 'ixvision_lldp_tag.py -u <username> -p <password> -t <tag1>,<tag2>,... [-h <hosts> | -f <host_file>] [-r port]'
    sys.exit(2)
for opt, arg in opts:
    if opt in ("-u", "--username"):
        username = arg
    elif opt in ("-p", "--password"):
        password = arg
    elif opt in ("-t", "--tags"):
        tags = arg.split(",")
    elif opt in ("-h", "--host"):
        host = arg
    elif opt in ("-f", "--hosts_file"):
        hosts_file = arg
    elif opt in ("-r", "--port"):
        port = arg

if username == '':
    print 'ixvision_lldp_tag.py -u <username> -p <password> -t <tag1>,<tag2>,... [-h <hosts> | -f <host_file>] [-r port]'
    sys.exit(2)

if password == '':
    print 'ixvision_lldp_tag.py -u <username> -p <password> -t <tag1>,<tag2>,... [-h <hosts> | -f <host_file>] [-r port]'
    sys.exit(2)

if (host == '') and (hosts_file == ''):
    print 'ixvision_lldp_tag.py -u <username> -p <password> -t <tag1>,<tag2>,... [-h <hosts> | -f <host_file>] [-r port]'
    sys.exit(2)

if len(tags) == 0:
    print 'ixvision_lldp_tag.py -u <username> -p <password> -t <tag1>,<tag2>,... [-h <hosts> | -f <host_file>] [-r port]'
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
    
    print("DEBUG: Starting thread for %s" % (host_ip))
    thread = threading.Thread(name=host, target=tag_ports, args=(host_ip, port, username, password, tags))
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




