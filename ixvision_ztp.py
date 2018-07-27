#!/usr/bin/env python
#
# Zeto-Touch Provisioning script (playbook) for a Ixia Vision NPB
#

# 1. Check and upgrade s/w version [SKIP]
# 2. Configure basic system parameters (login banner for example) [maybe as a test]
# 3. Install a license [SKIP]
# 4. Perform port inventory based on LLDP info, tag the ports discovered [FOCUS]
# 5. Configure LBGs for Tools: BRO, Moloch [after #4]
# 6. Created filters for BRO and Moloch, connect them to TAP and SPAN ports [after #4]

import sys
import getopt
import threading
import json
from ixia_nto import *

# DEFINE FUNCTIONS HERE

# Port inventory using LLDP info

# Input 
# - Connection to an NPB
# - NPB type (can be determined)
# - Supported port speeds per model (for now, we can assume 1 and 10G only)
# - ZTP scope (how many ports, for example) - we need this for granular control, instead of going through all available ports
# - Keywords to look for on network side
# - Keywords to look for on tool side

# Model to operate
# NPB
# |_Connection
# |_Type
# |_PortCapabilities[PortList[PortNum,SpeedList]]
# |_ZTPScope[PortList]
# |_Keywords[Names,Types[NP|TP]]
# |
# |_DiscoveredPortList[PortNum,Enabled,Type,Speed,Status,Keywords,ZTPSucceeded]

# Validate the NPB type againts a list of supported models [Exit if not supported]
# Pull port capabilities list for the NPB type [Exit if not exists]
# Pull ZTP scope [Assume all in scope if not exists]
# Overlay port capabilities with ZTP scope - initialize DiscoveredPortList with default values
# All actions from here happen only within ZTP scope

# TODO Disconnect all the filters from the ports in scope
# Enable all disabled ports as 10G, NP - collect status
# Reconfigure ports that are down as 1G - collect status
# Disable all disconnected ports, set them as network, 10G

# Quiery NPB for port configs and status
# Use optional keyword to limit the inventory scope to ports tagged by matching keyword
def portInventory(host_ip, port, username, password, keyword=''):

    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port, debug=True, logFile="ixvision_ztp_debug.log")

    discoveredPortList = {}

    # Enumerate disabled ports - we are not touching anything that can already carry traffic
    searchTerms = {'enabled':False}
    if keyword != '':
        # Limit ZTP scope by a keyword if provided
        searchTerms = {"keywords":[keyword],'enabled':False}
        
    for ntoPort in nto.searchPorts(searchTerms):
        ntoPortDetails = nto.getPort(str(ntoPort['id']))
        print("DEBUG: Collected port %s:%s configuration" % (host_ip, ntoPortDetails['default_name']))
        discoveredPortList[ntoPort['id']] = {'name': ntoPortDetails['default_name'], 'type': 'port', 'ZTPSucceeded': False, 'details': ntoPortDetails}
        
    if len(discoveredPortList) == 0:
        return
    
    f = open(host_ip + '_pre_ztp_config.txt', 'w')
    f.write(json.dumps(discoveredPortList))
    f.close()

    # TODO Disconnect all the filters from the ports in scope

    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        if port['details']['media_type'] == 'SFP_PLUS_10G' and port['details']['mode'] == 'NETWORK':
            # Enable such ports
            if 'enabled' in port['details']:
                nto.modifyPort(str(port_id), {'enabled': True})
                print("DEBUG: Enabled port %s:%s" % (host_ip, port['details']['default_name']))
        else:
            if port['details']['media_type'] == 'SFP_1G':
                # Convert such ports to 10G
                nto.modifyPort(str(port_id), {'media_type': 'SFP_PLUS_10G','link_settings': '10G_FULL'})
                print("DEBUG: Converted port %s:%s to 10G" % (host_ip, port['details']['default_name']))
            if port['details']['mode'] != 'NETWORK':
                # Convert such ports to NETWORK
                nto.modifyPort(str(port_id), {'mode': 'NETWORK'})
                print("DEBUG: Converted port %s:%s to NETWORK" % (host_ip, port['details']['default_name']))
            # Validate new settings took effect
            portDetails = nto.getPort(str(port_id))
            if portDetails['media_type'] == 'SFP_PLUS_10G' and portDetails['mode'] == 'NETWORK':
                # Enable the port
                if 'enabled' in port['details']:
                    nto.modifyPort(str(port_id), {'enabled': True})
                    print("DEBUG: Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                    
    # Pause the thread to give the ports a chance to come up
    time.sleep(10)
    print('')
    
    # Collect link status for ports in scope
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        ntoPortDetails = nto.getPort(str(port_id))
        print("DEBUG: Collected port %s:%s status:" % (host_ip, ntoPortDetails['default_name'])),
        if ntoPortDetails['link_status']['link_up']:
            print('UP')
            discoveredPortList[port_id] = {'ZTPSucceeded': True}
        else:
            print('DOWN')
            discoveredPortList[port_id] = {'ZTPSucceeded': False}
        # Update the list with the latest config and status
        discoveredPortList[port_id]['details'] = ntoPortDetails

    # Now go through the ports that are still down and change the media to 1G/AUTO
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        portDetails = port['details']
        if not portDetails['link_status']['link_up'] and portDetails['enabled'] and portDetails['media_type'] == 'SFP_PLUS_10G':
            nto.modifyPort(str(port_id), {'media_type': 'SFP_1G','link_settings': 'AUTO','mode': 'NETWORK'})
            print("DEBUG: Converted port %s:%s to 1G/Auto, NETWORK" % (host_ip, port['details']['default_name']))
        
    # Pause the thread to give the ports a chance to come up
    time.sleep(10)
    print('')

    # Collect link status for ports in scope
    # TODO DRY
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        ntoPortDetails = nto.getPort(str(port_id))
        print("DEBUG: Collected port %s:%s status:" % (host_ip, ntoPortDetails['default_name'])),
        if ntoPortDetails['link_status']['link_up']:
            print('UP')
            discoveredPortList[port_id] = {'ZTPSucceeded': True}
        else:
            print('DOWN')
            discoveredPortList[port_id] = {'ZTPSucceeded': False}
        # Update the list with the latest config and status
        discoveredPortList[port_id]['details'] = ntoPortDetails

    # Enable LLDP TX on all enabled ports in scope
    # For all ports where ZTP failed by this point, set them as network, 10G and disable
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        portDetails = port['details']
        if port['ZTPSucceeded']:
            if 'lldp_receive_enabled' in portDetails: # check if this port has LLDP support before enabling it
                nto.modifyPort(str(port_id), {'lldp_receive_enabled': True, 'keywords': ['_ZTP_LLDP']})
                print("DEBUG: Enabled LLDP on port %s:%s" % (host_ip, port['details']['default_name']))
            else:
                print("DEBUG: Port %s:%s doesn't have LLDP RX capabilities" % (host_ip, port['details']['default_name']))
        else:
            nto.modifyPort(str(port_id), {'enabled': False, 'media_type': 'SFP_PLUS_10G', 'link_settings': '10G_FULL', 'mode': 'NETWORK'})
            print("DEBUG: Converted port %s:%s to 10G, NETWORK and DISABLED" % (host_ip, port['details']['default_name']))


# Main thread

argv = sys.argv[1:]
username = ''
password = ''
keyword = ''    # USING KEYWORD ARG HERE TEMP TO DEFINE ZTP SCOPE
host = ''
hosts_file = ''
config_file = ''
port = 8000

try:
    opts, args = getopt.getopt(argv,"u:p:k:h:f:r:", ["username=", "password=", "keyword=", "host=", "hosts_file=", "port="])
except getopt.GetoptError:
    print 'ixvision_ztp.py -u <username> -p <password> -k <keyword> [-h <hosts> | -f <host_file>] [-r port]'
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
    print 'ixvision_ztp.py -u <username> -p <password> [-h <hosts> | -f <host_file>] [-r port] [-k <keyword>]'
    sys.exit(2)

if password == '':
    print 'ixvision_ztp.py -u <username> -p <password> [-h <hosts> | -f <host_file>] [-r port] [-k <keyword>]'
    sys.exit(2)

if (host == '') and (hosts_file == ''):
    print 'ixvision_ztp.py -u <username> -p <password> [-h <hosts> | -f <host_file>] [-r port] [-k <keyword>]'
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
    thread = threading.Thread(name=host, target=portInventory, args=(host_ip, port, username, password, keyword))
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




