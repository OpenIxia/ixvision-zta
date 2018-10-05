# Zero-Touch Provisioning script (playbook) for a Ixia Vision NPB
# Perform initial NPB configuration, run through port discovery.
# End goal is to have a managable system with LLDP neighbours being observed for further ZTP configuration steps

# 1. Check and upgrade s/w version [SKIP]
# 2. Configure basic system parameters (login banner for example) [maybe as a test]
# 3. Install a license [SKIP]
# 4. Perform port discovery - cycle through all supported port speeds to brning all possible links up [FOCUS]
# 5. Disable all the ports that stayed down, tag the ports that came up as configured by ZTP

from ixia_nto import *

# DEFINE FUNCTIONS HERE

# Input 
# - Connection to an NPB
# - NPB type (can be determined)
# - Supported port speeds per model (for now, we can assume 1 and 10G only)
# - ZTP scope (how many ports, for example) - we need this for granular control, instead of going through all available ports

# Model to operate
# NPB
# |_Connection
# |_Type
# |_PortCapabilities[PortList[PortNum,SpeedList]]
# |_ZTPScope[PortList]
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
def discover_ports(host_ip, port, username, password, keyword=''):

    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port, debug=True, logFile="ixvision_ztp_debug.log")

    discoveredPortList = {}

    # Enumerate disabled ports - we are not touching anything that can already carry traffic
    searchTerms = {'enabled':False}
    if keyword != None and keyword != '':
        # Limit ZTP scope by a keyword if provided
        searchTerms = {"keywords":[keyword],'enabled':False}
        
    for ntoPort in nto.searchPorts(searchTerms):
        ntoPortDetails = nto.getPort(str(ntoPort['id']))
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
                print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
        else:
            if port['details']['media_type'] == 'SFP_1G':
                # Convert such ports to 10G
                nto.modifyPort(str(port_id), {'media_type': 'SFP_PLUS_10G','link_settings': '10G_FULL'})
                print("Converted port %s:%s to 10G" % (host_ip, port['details']['default_name']))
            if port['details']['mode'] != 'NETWORK':
                # Convert such ports to NETWORK
                nto.modifyPort(str(port_id), {'mode': 'NETWORK'})
                print("Converted port %s:%s to NETWORK" % (host_ip, port['details']['default_name']))
            # Validate new settings took effect
            portDetails = nto.getPort(str(port_id))
            if portDetails['media_type'] == 'SFP_PLUS_10G' and portDetails['mode'] == 'NETWORK':
                # Enable the port
                if 'enabled' in port['details']:
                    nto.modifyPort(str(port_id), {'enabled': True})
                    print("Enabled port %s:%s" % (host_ip, port['details']['default_name']))
                    
    # Pause the thread to give the ports a chance to come up
    time.sleep(10)
    print('')
    
    # Collect link status for ports in scope
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        ntoPortDetails = nto.getPort(str(port_id))
        print("Collected port %s:%s status:" % (host_ip, ntoPortDetails['default_name'])),
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
            print("Converted port %s:%s to 1G/Auto, NETWORK" % (host_ip, port['details']['default_name']))
        
    # Pause the thread to give the ports a chance to come up
    time.sleep(10)
    print('')

    # Collect link status for ports in scope
    # TODO DRY
    for port_id in discoveredPortList:
        port = discoveredPortList[port_id]
        ntoPortDetails = nto.getPort(str(port_id))
        print("Collected port %s:%s status:" % (host_ip, ntoPortDetails['default_name'])),
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
                nto.modifyPort(str(port_id), {'lldp_receive_enabled': True, 'keywords': ['ZTP']})
                print("Enabled LLDP on port %s:%s" % (host_ip, port['details']['default_name']))
            else:
                print("Port %s:%s doesn't have LLDP RX capabilities" % (host_ip, port['details']['default_name']))
        else:
            nto.modifyPort(str(port_id), {'enabled': False, 'media_type': 'SFP_PLUS_10G', 'link_settings': '10G_FULL', 'mode': 'NETWORK'})
            print("Converted port %s:%s to 10G, NETWORK and DISABLED" % (host_ip, port['details']['default_name']))



