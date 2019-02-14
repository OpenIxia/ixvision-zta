###############################################################################
#
# Zero-Touch Automation utility for Ixia Vision Network Packet Brokers
#
# File: ixvision_ztp_sysinfo.py
# Author: Alex Bortok (https://github.com/bortok)
#
# Description: A module to inquiry system status
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

# Model to operate
# NPB
# |_Connection
# |_Type

def print_sysinfo(name, value):
    print("%s%s%s" % (name, ' ' * (20 - len(name)), value))

def nto_get_sysinfo(host_ip, port, username, password):
    
    sysinfo_strings = {
        'name': 'System name:',\
        'location': 'Location:',\
        'contact_info': 'Contact:',\
        'ipv4_address': 'Management IPv4:',\
        'ipv6_address': 'Management IPv6:',\
        'mac_address': 'MAC:',\
        'software_version': 'Software ver.:',\
        'part_num': 'Part number:',\
        'serial_num': 'Serial:'
    }

    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port, debug=False, logFile="ixvision_status_debug.log")

    nto_system_properties = nto.getSystem()
    nto_system_info = nto_system_properties['system_info']
    nto_ip_info = nto_system_properties['ip_config']
    nto_hardware_info = nto.getLoginInfo()['hardware_info']
    
    print_sysinfo(sysinfo_strings['name'], nto_system_info['name'])
    print_sysinfo(sysinfo_strings['location'], nto_system_info['location'])
    print_sysinfo(sysinfo_strings['contact_info'], nto_system_info['contact_info'])
    print

    print_sysinfo(sysinfo_strings['ipv4_address'], nto_ip_info['ipv4_address'])
    print_sysinfo(sysinfo_strings['ipv6_address'], nto_ip_info['ipv6_address'])
    print_sysinfo(sysinfo_strings['mac_address'], ':'.join(nto_hardware_info['mac_address'][i:i+2] for i in range(0,12,2)).upper())
    print

    print_sysinfo(sysinfo_strings['software_version'], nto_system_properties['software_version'])
    print
    
    for module in nto_hardware_info['module_list']:
        if module['id']['module_type'] == 'MAIN':
            print_sysinfo(sysinfo_strings['part_num'], module['part_num'])
            print_sysinfo(sysinfo_strings['serial_num'], module['serial_num'])
            print