#!/usr/bin/env python
#
# Zero-Touch Provisioning script (playbook) for a Ixia Vision NPB
# Form a port group based on keywords the ports are tagged with

# 1. Starting point is an Ixia Vision NPB with ports tagged by certain keywords that indicate what is connected to them
# 2. Each run of this script would configure a single port group using the supplied name and group type:
#  - Search for an existing port group with the same name. If found with the matching type, continue by referencing that group. If the type doesn't match, stop. 
#  - If not found, create a new group
# 4. Search for enabled ports with matching keywords that are not yet members of any group and don't have any connections to/from them. Add all such ports to the group, change port mode if nessesary
# 5. For all exising port group members, check keywords and if any have no match, remove them from the port group and set to a default configuration (Network Port, no connections)


import sys
import getopt
import threading
import json
from ixia_nto import *

# DEFINE FUNCTIONS HERE

# Input 
# - Connection to an NPB
# - Keywords to use for matching ports
# - Port group name
# - Port group type: "net" for network (interconnect), "lb" for load balanced tool group

# Model to operate
# NPB
# |_Connection
# |_Type
# |_Keywords[Names]

def form_port_groups(host_ip, port, username, password, tags, pg_name, pg_mode_key):
    if pg_mode_key == 'lb' or pg_mode_key == 'LB':
        pg_params = {'mode': 'TOOL', 'port_group_type': 'LOAD_BALANCE'}
    else:   # Inside this function we will default to Network Port Group mode
        pg_params = {'mode': 'NETWORK', 'port_group_type': 'INTERCONNECT'}
        
    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port, debug=True, logFile="ixvision_ztp_port_group_debug.log")

    port_group_list = nto.searchPortGroups({'name': pg_name})
    ztp_port_group = None
    ztp_port_group_port_list = []
    if len(port_group_list) == 0:
        # No existing group with such name, create new one
        pg_params.update({'name': pg_name, 'keywords': ['_ZTP_LLDP'] + tags})
        new_port_group = nto.createPortGroup(pg_params)
        if new_port_group is not None and len(new_port_group) > 0:
            print("No group found, created a new one with id %s" % (str(new_port_group['id'])))
            ztp_port_group = new_port_group
        else:
            print("No group found, failed to created a new one!")
            return
    elif len(port_group_list) == 1:
        # An existing port group found
        port_group = port_group_list[0]
        port_group_details = nto.getPortGroup(str(port_group['id']))
        if port_group_details is not None:
            # WARNING! NTO API returns 'type' attribute instead of 'port_group_type'
            print("Found existing port group %s of %s type and %s mode" % (port_group_details['default_name'], port_group_details['type'], port_group_details['mode'])),
            if port_group_details['type'] == pg_params['port_group_type'] and port_group_details['mode'] == pg_params['mode']:
                # PG types match, will update the existing group
                print("-- type and mode match, will update")
                ztp_port_group = port_group
                ztp_port_group_port_list = port_group_details['port_list']
                # Update keywords
                updated_keywords = []
                updated_keywords.extend(port_group_details['keywords'])
                for keyword in tags:
                    if keyword not in updated_keywords:
                        updated_keywords.append(keyword)
                if len(updated_keywords) > len(port_group_details['keywords']):
                    nto.modifyPortGroup(str(port_group['id']),{'keywords': updated_keywords})
            else:
                # Mismatch, return
                print("-- type or mode mismatch with requested %s, %s, skipping..." % (pg_params['port_group_type'], pg_params['mode']))
        else:
            print("Failed to retrieve details for port %s, skipping..." % (port_group['name']))
    else:
        # This should never happen, but just in case, provide details to look into
        print("Found more than one port group named %s, can't continue:" % (port_group['name'])),
        for port_group in port_group_list:
            port_group_details = nto.getPortGroup(str(port_group['id']))
            if port_group_details is not None:
                print (" %s," % (port_group_details['default_name'])),
        print("")
        return

    # Now search for ports to be added to the port group
    port_list = nto.searchPorts({'enabled': True, 'port_group_id': None, 'dest_filter_list': [], 'source_filter_list': []})
    matching_port_id_list = []
    for port in port_list:
        port_details = nto.getPortProperties(str(port['id']), 'id,keywords,mode')
        if port_details is not None:
            for keyword in tags:
                if keyword in port_details['keywords']:
                    # TODO rework this to simplify since now matching_port_id_list is a simple array
                    already_matched = False  # Will check if we already matched this port via a different tag
                    for matched_port_id in matching_port_id_list:
                        if port['id'] == matched_port_id:
                            already_matched = True
                    if not already_matched:
                        print("Found port %s with matching keyword %s" % (port['name'], keyword))
                        matching_port_id_list.append(port['id'])
                        # Check and update port mode, if needed
                        if port_details['mode'] != pg_params['mode']:
                            print("Convering port %s into %s mode" % (port['name'], pg_params['mode']))
                            nto.modifyPort(str(port['id']), {'mode': pg_params['mode']})
                            # TODO check if the modification was successful
                
    if len(matching_port_id_list) == 0:
        print("No matching ports found")
        return
    else:
        print("Found %d matching ports" % (len(matching_port_id_list)))
        
        
    nto.modifyPortGroup(str(ztp_port_group['id']), {'port_list': matching_port_id_list + ztp_port_group_port_list})
    print("Added %d ports to port group %s" % (len(matching_port_id_list), pg_name))




# Main thread

argv = sys.argv[1:]
username = ''
password = ''
tags = []               # A list of keywords to match port keywords info againts
port_group_name = ''    # Name for the group to use (in order to avoid referencing automatically generated group number)
port_group_mode = ''    # (net) for NETWORK, (lb) for LOAD_BALANCE - no other modes are supported yet
host = ''
hosts_file = ''
config_file = ''
port = 8000

usage = 'ixvision_lldp_tag.py -u <username> -p <password> -t <tag1>,<tag2>,... -n <port_group_name> -m net|lb [-h <hosts> | -f <host_file>] [-r port]'

try:
    opts, args = getopt.getopt(argv,"u:p:h:f:r:t:n:m:", ["username=", "password=", "host=", "hosts_file=", "port=", "tags=", "name=", "mode="])
except getopt.GetoptError:
    print usage
    sys.exit(2)
for opt, arg in opts:
    if opt in ("-u", "--username"):
        username = arg
    elif opt in ("-p", "--password"):
        password = arg
    elif opt in ("-t", "--tags"):
        tags = arg.upper().split(",")  # NTO keywords are always in upper case
    elif opt in ("-n", "--name"):
        port_group_name = arg
    elif opt in ("-m", "--mode"):
        port_group_mode = arg
    elif opt in ("-h", "--host"):
        host = arg
    elif opt in ("-f", "--hosts_file"):
        hosts_file = arg
    elif opt in ("-r", "--port"):
        port = arg

if username == '':
    print usage
    sys.exit(2)

if password == '':
    print usage
    sys.exit(2)

if (host == '') and (hosts_file == ''):
    print usage
    sys.exit(2)

if len(tags) == 0:
    print usage
    sys.exit(2)

if port_group_name == '':
    print usage
    sys.exit(2)

if port_group_mode != 'net' and port_group_mode != 'lb':
    print usage
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
    thread = threading.Thread(name=host, target=form_port_groups, args=(host_ip, port, username, password, tags, port_group_name, port_group_mode))
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




