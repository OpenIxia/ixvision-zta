###############################################################################
#
# Zero-Touch Automation utility for Ixia Vision Network Packet Brokers
#
# File: ixvision_ztp_lldp_tag.py
# Author: Alex Bortok (https://github.com/bortok)
#
# Description: Tag ports with keywords matched with LLDP info
# Since this script doesn't change any operational parameters of an NPB, it could be run as often as needed to keep the port tags updated
# 1. Starting point is an Ixia Vision NPB with all required ports enabled and receiving LLDP info from neighbors
# 2. Input parameters to this script enumerate which keywords to look in LLDP Port Description field
# 3. Connect to an NPB and collect LLDP Neighbors info
# 4. Compare LLDP Port Description info with supplied keywords, identify matches
# 5. Tag indentified ports with the matching keywords
#
# COPYRIGHT 2018 - 2019 Keysight Technologies.
#
# This code is provided under the MIT license.  
# You can find the complete terms in LICENSE.txt
#
###############################################################################


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

# TODO remove keywords from ports that no longer have matching LLDP neighbors

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
