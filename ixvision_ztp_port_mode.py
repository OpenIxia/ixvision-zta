###############################################################################
#
# Zero-Touch Automation utility for Ixia Vision Network Packet Brokers
#
# File: ixvision_ztp_port_mode.py
# Author: Alex Bortok (https://github.com/bortok)
#
# Description: A module to set port mode for ports with matching tags
#
# COPYRIGHT 2018 - 2019 Keysight Technologies.
#
# This code is provided under the MIT license.  
# You can find the complete terms in LICENSE.txt
#
###############################################################################

from ixia_nto import *

from ixvision_ztp_ntolib import *

# DEFINE VARs HERE

# DEFINE FUNCTIONS HERE

# Input 
# - Connection to an NPB
# - Keywords to use for matching ports
# - Port type: "net" for network, "tool" for tool ports

def set_port_mode(host_ip, port, username, password, tags, mode):

    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port, debug=True, logFile="ixvision_ztp_port_mode_debug.log")

    # Search for ports to be updated - can't be a part of a port group, can't have any existing connections
    port_list = nto.searchPorts({'enabled': True, 'port_group_id': None, 'dest_filter_list': [], 'source_filter_list': []})
    matching_port_id_list = []
    for port in port_list:
        port_details = nto.getPortProperties(str(port['id']), 'id,keywords,mode')
        if port_details is not None:
            for keyword in tags:
                if keyword.upper() in port_details['keywords'] and port['id'] not in matching_port_id_list and port_details['mode'] != port_modes_supported[mode]:
                    matching_port_id_list.append(port['id'])
                    print("Found port %s with matching keyword %s in mode %s" % (port['name'], keyword.upper(), port_details['mode']))
                
    if len(matching_port_id_list) == 0:
        print("No mode update requied for ports with keywords %s" % ", ".join(tags))
        return
    
    # Update port mode
    print("Convering ports into %s mode" % (port_modes_supported[mode]))
    for port_id in matching_port_id_list:
        nto.modifyPort(str(port_id), {'mode': port_modes_supported[mode]})
        # Check if the modification was successful and only add the port to the list of matching ports if yes
        port_details = nto.getPortProperties(str(port_id), 'id,name,mode')
        if port_details is not None and port_details['mode'] == port_modes_supported[mode]:
            print("Port %s mode update succeeded" % port_details['name'])
        else:
            print("Port %s mode update failed!" % port_details['name'])
