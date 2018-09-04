#!/usr/bin/env python
#
# Zero-Touch Provisioning script (playbook) for a Ixia Vision NPB
# Create/update a dynamic filter between network and tool port groups 

# 1. Starting point is an Ixia Vision NPB with network and tool port groups formed
# 2. Each run of this script would configure a single dynamic filter using supplied name and filter criteria
#  - Search for an existing DF with the same name. If found with the matching type, continue by referencing that DF
#  - If not found, create a new DF
# 3. Update the DF criteria with provided rules
# 4. Search for network port group with a specified name and, if found, connect it to the input of the DF
# 5. Search for tool port group with a specified name and, if found, connect it to the output of the DF


import sys
import getopt
import threading
import json
from ixia_nto import *

# DEFINE GLOBAL VARs HERE
# NOTE - Priority-based filtering mode is not supported, but we don't check if the system is in such mode
df_modes_supported = {'all': 'PASS_ALL', 'none': 'DISABLE', 'pbc': 'PASS_BY_CRITERIA', 'dbc': 'DENY_BY_CRITERIA', 'pbcu': 'PBC_UNMATCHED', 'dbcm': 'DBC_MATCHED'}

# DEFINE FUNCTIONS HERE

# Check if DF mode used requires a criteria
def df_criteria_required(df_mode):
    return df_mode in df_modes_supported and (df_mode == 'pbc' or df_mode == 'dbc')

## Search for port groups and return a list if IDs
def search_port_group_id_list(nto, params):
    pg_id_list = []
    pg_list = nto.searchPortGroups(params)
    for pg in pg_list:
        pg_id_list.append(pg['id'])
    return pg_id_list

## Remove empty port groups from a list if port group IDs
def remove_empty_port_groups_from_id_list(nto, pg_id_list):
    non_empty_pg_id_list = []
    for pg_id in pg_id_list:
        pg_port_list = nto.getPortGroupProperty(str(pg_id), 'port_list')
        if isinstance(pg_port_list, list) and len(pg_port_list) > 0:
            non_empty_pg_id_list.append(pg_id)
    return non_empty_pg_id_list

## Filter create/update

# Input 
# - Connection to an NPB
# - Dynamic filter name
# - Network port group name
# - Tool port group name
# - DF mode - use keys from df_modes_supported global dict

def form_dynamic_filter(host_ip, port, username, password, df_name, input_pg_name, output_pg_name, df_mode, df_criteria = {}):
    
    df_params = {}
    df_mode_value = 'DISABLE'                           # Default DF mode value for a new filter to use, if not overridden

    if isinstance(df_modes_supported, dict) and df_mode in df_modes_supported.keys():
        df_mode_value = df_modes_supported[df_mode]
        
    if df_criteria_required(df_mode) and (isinstance(df_criteria, dict) and len(df_criteria) == 0 or not isinstance(df_criteria, dict)):
        print("Non-empty criteria are required for filter mode %s" % (df_mode))
        return
                
    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port, debug=True, logFile="ixvision_ztp_filter_debug.log")

    # Search for existing DF, create a new one if not found
    df_list = nto.searchFilters({'name': df_name})
    ztp_df = None
    ztp_df_source_port_group_id_list = []
    ztp_df_dest_port_group_id_list = []
    if len(df_list) == 0:
        # No existing filter with such name, will create a new one
        df_params.update({'name': df_name, 'keywords': ['_ZTP_LLDP'], 'mode': df_mode_value})
        if isinstance(df_criteria, dict) and len(df_criteria) > 0:
            df_params.update({'criteria': df_criteria})
        new_df = nto.createFilter(df_params, True) # the last parameter is for allowTemporayDataLoss
        if new_df is not None and len(new_df) > 0:
            print("No existing DF found, created a new one with id %s" % (str(new_df['id'])))
            ztp_df = new_df
        else:
            print("No existing DF found, failed to created a new one!")
            return
    elif len(df_list) == 1:
        # An existing DF found
        df = df_list[0]
        df_details = nto.getFilter(str(df['id'])) # TODO handle 404 not found situation
        ztp_df = df
        ztp_df_source_port_group_id_list = df_details['source_port_group_list']
        ztp_df_dest_port_group_id_list = df_details['dest_port_group_list']
        print("Found an existing DF %s in %s mode" % (df_details['default_name'], df_details['mode']))
        df_needs_updating = False
        # TODO update keywords with _ZTP_LLDP
        if df_mode_value != df_details['mode']:
            print("Updating DF %s to a new mode %s" % (df_details['default_name'], df_mode_value))
            df_params.update({'mode': df_mode_value})
            df_needs_updating = True
        if isinstance(df_criteria, dict) and len(df_criteria) > 0:
            df_criteria.update(df_details['criteria'])
            if df_criteria != df_details['criteria']:
                print("Updating DF %s criteria" % (df_details['default_name']))
                df_params.update({'criteria': df_criteria})
                df_needs_updating = True
        if df_needs_updating:
            nto.modifyFilter(str(df['id']), df_params)
        # TODO handle errors
    else:
        # This should never happen, but just in case, provide details to look into
        print("Found more than one DF named %s, can't continue:" % (df_name)),
        for df in df_list:
            df_details = nto.getFilter(str(df['id']))
            if df_details is not None:
                print (" %s," % (df_details['default_name'])),
        print("")
        return
        
    # TODO update DF criteria
    
    # Search for network and tool port groups matching given names. 
    # Make sure they are not empty before connecting to filters, since ports can't be added later to an empty but connected port group
            
    ztp_df_source_port_group_id_list.extend(remove_empty_port_groups_from_id_list(nto, search_port_group_id_list(nto, {'name': input_pg_name})))
    ztp_df_dest_port_group_id_list.extend  (remove_empty_port_groups_from_id_list(nto, search_port_group_id_list(nto, {'name': output_pg_name})))
    
    # TODO update DF connections only if there is an actual change in list of PGs connected to it
    df_params.update({'source_port_group_list': ztp_df_source_port_group_id_list, 'dest_port_group_list': ztp_df_dest_port_group_id_list})
    nto.modifyFilter(str(ztp_df['id']), df_params)

# Main thread

argv = sys.argv[1:]
username = ''
password = ''
df_name = ''            # Name for Dynamic Filter to work with
network_pg_name = ''    # Name for the network port group to connect to the DF
tool_pg_name = ''       # Name for the tool port group to connect to the DF
df_mode = ''            # Mode for Dynamic Filter
criteria_file = ''      # File with dynamic filter criteria in JSON format
df_criteria = None      # Criteria for Dynamic Filter after pasing criteria_file
host = ''
hosts_file = ''
config_file = ''
port = 8000

usage = 'ixvision_ztp_filter.py -u <username> -p <password> -n <dynamic_filter_name> -i <network_port_group_name> -o <tool_port_group_name> -m all|none|pbc|dbc|pbcu|dbcm -c <filter_criteria_file> [-h <hosts> | -f <host_file>] [-r port]'

try:
    opts, args = getopt.getopt(argv,"u:p:h:f:r:n:i:o:m:c:", ["username=", "password=", "host=", "hosts_file=", "port=", "name=", "input=", "output=", "mode=", "criteria_file="])
except getopt.GetoptError:
    print usage
    sys.exit(2)
for opt, arg in opts:
    if opt in ("-u", "--username"):
        username = arg
    elif opt in ("-p", "--password"):
        password = arg
    elif opt in ("-n", "--name"):
        df_name = arg
    elif opt in ("-i", "--input"):
        network_pg_name = arg
    elif opt in ("-o", "--output"):
        tool_pg_name = arg
    elif opt in ("-m", "--mode"):
        if arg.lower() in df_modes_supported.keys():
            df_mode = arg
        else:
            print("Unsupported filter mode %s" % (arg))
    elif opt in ("-c", "--criteria_file"):
        criteria_file = arg
    elif opt in ("-h", "--host"):
        host = arg
    elif opt in ("-f", "--hosts_file"):
        hosts_file = arg
    elif opt in ("-r", "--port"):
        port = arg

if username == '' or password == '':
    print usage
    sys.exit(2)

if (host == '') and (hosts_file == ''):
    print usage
    sys.exit(2)

if df_name == '' or network_pg_name == '' or tool_pg_name == '' or df_mode == '':
    print usage
    sys.exit(2)
    
if df_criteria_required(df_mode) and criteria_file == '':
    print ("Error: criteria file is requied for dynamic filter mode %s" % (df_mode))
    sys.exit(2)

if criteria_file != '':
    parse_failed = False
    try:
        with open(criteria_file) as f:
            try:
                df_criteria = json.load(f)
                print("Filter criteria has been loaded")
            except:
                print("Error: can't parse filter criteria")
                parse_failed = True
                sys.exit(2)
    except:
        if not parse_failed:
            print("Error: can't read the file with filter criteria")
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
    thread = threading.Thread(name=host, target=form_dynamic_filter, args=(host_ip, port, username, password, df_name, network_pg_name, tool_pg_name, df_mode, df_criteria))
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




