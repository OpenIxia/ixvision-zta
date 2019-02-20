###############################################################################
#
# Zero-Touch Automation utility for Ixia Vision Network Packet Brokers
#
# File: ixvision_ztp_port_group.py
# Author: Alex Bortok (https://github.com/bortok)
#
# Description: Form a port group based on keywords the ports are tagged with
# 1. Starting point is an Ixia Vision NPB with ports tagged by certain keywords that indicate what is connected to them
# 2. Each run of this script would configure a single port group using the supplied name and group type:
#  - Search for an existing port group with the same name. If found with the matching type, continue by referencing that group. If the type doesn't match, stop. 
#  - If not found, create a new group
# 4. Search for enabled ports with matching keywords that are not yet members of any group and don't have any connections to/from them. Add all such ports to the group, change port mode if nessesary
# 5. For all exising port group members, check keywords and if any have no match, remove them from the port group and set to a default configuration (Network Port, no connections)
#
# COPYRIGHT 2018 - 2019 Keysight Technologies.
#
# This code is provided under the MIT license.  
# You can find the complete terms in LICENSE.txt
#
###############################################################################

from ixia_nto import *

# DEFINE VARs HERE
pg_modes_supported = {'net': 'INTERCONNECT', 'lb': 'LOAD_BALANCE'}


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
    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port, debug=True, logFile="ixvision_ztp_port_group_debug.log")
    
    # Check s/w version to use proper API syntax (ixia_nto.py doesn't support API versioning)
    nto_system_properties = nto.getSystem()
    nto_major_version = int(nto_system_properties['software_version'][0])
    
    if nto_major_version == 4:
        pg_type_key = 'port_group_type'
    else:
        pg_type_key = 'type'

    if pg_mode_key == 'lb' or pg_mode_key == 'LB':
        pg_params = {'mode': 'TOOL', pg_type_key: 'LOAD_BALANCE'}
    else:   # Inside this function we will default to Network Port Group mode
        pg_params = {'mode': 'NETWORK', pg_type_key: 'INTERCONNECT'}
        

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
            # WARNING! All NTO API versions returns 'type' attribute key on GET, but not on CREATE/UPDATE
            print("Found existing port group %s of %s type and %s mode" % (port_group_details['default_name'], port_group_details['type'], port_group_details['mode'])),
            if port_group_details['type'] == pg_params[pg_type_key] and port_group_details['mode'] == pg_params['mode']:
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
                print("-- type or mode mismatch with requested %s, %s, skipping..." % (pg_params[pg_type_key], pg_params['mode']))
                return
        else:
            print("Failed to retrieve details for port %s, skipping..." % (port_group['name']))
    else:
        # This should never happen, but just in case, provide details to look into
        print("Found more than one port group named %s, can't continue:" % (pg_name)),
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
                if keyword in port_details['keywords'] and port['id'] not in matching_port_id_list:
                        print("Found port %s with matching keyword %s" % (port['name'], keyword))
                        # Check and update port mode, if needed
                        if port_details['mode'] == pg_params['mode']:
                                matching_port_id_list.append(port['id'])
                        else:
                            print("Convering port %s into %s mode" % (port['name'], pg_params['mode']))
                            nto.modifyPort(str(port['id']), {'mode': pg_params['mode']})
                            # Check if the modification was successful and only add the port to the list of matching ports if yes
                            port_details = nto.getPortProperties(str(port['id']), 'id,keywords,mode')
                            if port_details is not None and port_details['mode'] == pg_params['mode']:
                                matching_port_id_list.append(port['id'])
                            else:
                                # Note, if the same port has several keywords that match, there will be several attempts to change the mode
                                print("Changing port mode failed, skipping...")
                
    if len(matching_port_id_list) == 0:
        print("No matching ports found")
        return
    else:
        print("Found %d matching ports" % (len(matching_port_id_list)))
        
        
    nto.modifyPortGroup(str(ztp_port_group['id']), {'port_list': matching_port_id_list + ztp_port_group_port_list})
    print("Added %d ports to port group %s" % (len(matching_port_id_list), pg_name))


