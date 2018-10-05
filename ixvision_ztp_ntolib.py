# Zero-Touch Provisioning script (playbook) for a Ixia Vision NPB
# Common ZTP library of methods for interacting with NTO

from ixia_nto import *

# DEFINE VARs HERE
port_modes_supported = {'net': 'NETWORK', 'tool': 'TOOL'}
df_connection_modes_supported = {'input': 'NETWORK', 'output': 'TOOL'}
df_criteria_fields_supported = {'ip': 'ipv4_src_or_dst', 'ip-src': 'ipv4_src', 'ip-dst': 'ipv4_dst'}

# DEFINE FUNCTIONS HERE

# Connect an existing dynamic filter to a set of ports via keyword search
# Input 
# - NTO object as a connection to an NPB
# - Dynamic filter ID
# - Ports keywords to search for
# - Direction of the connection - input or output
def df_connect_via_tags(nto, df_id, tags, connection_mode):
    # Check the connection mode is supported
    if connection_mode not in df_connection_modes_supported.keys():
        print("Error: connection mode %s is not supported" % connection_mode)
        return
    
    # Search for ports to be connected - can't be a part of port group. Must already be in the required mode
    port_list = nto.searchPorts({'enabled': True, 'port_group_id': None, 'mode': df_connection_modes_supported[connection_mode]})
    matching_port_id_list = []
    for port in port_list:
        port_details = nto.getPortProperties(str(port['id']), 'id,keywords,mode')
        if port_details is not None:
            for keyword in tags:
                if keyword in port_details['keywords'] and port['id'] not in matching_port_id_list:
                    matching_port_id_list.append(port['id'])
                    print("Found port %s with ID %d, matching mode and keyword %s" % (port['name'], port['id'], keyword))
                
    if len(matching_port_id_list) == 0:
        print("No matching ports found with keywords %s" % " ".join(tags))
        return
    else:
        print("Found %d matching ports" % (len(matching_port_id_list)))

    # Retrieve a list of existing ports connected to the DF
    if connection_mode == 'input':
        df_property = 'source_port_list'
    else:
        df_property = 'dest_port_list'
        
    connect_list = nto.getFilterProperty(df_id, df_property) # TODO handle 404 not found situation
    connect_count_current = len(connect_list)
    for port_id in matching_port_id_list:
        if port_id not in connect_list:
            connect_list.extend([port_id])
    
    # Update the filter connections if there is a change needed
    if len(connect_list) != connect_count_current:
        print("Updating %s filter connections with port IDs: %s" % (connection_mode, " ".join(str(i) for i in matching_port_id_list)))
        nto.modifyFilter(df_id, {df_property: connect_list})
    else:
        print("No changes to %s filter connections are needed" % connection_mode)
    