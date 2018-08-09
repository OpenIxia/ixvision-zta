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

# DEFINE FUNCTIONS HERE

# Input 
# - Connection to an NPB
# - Dynamic filter name
# - Network port group name
# - Tool port group name

def form_dynamic_filter(host_ip, port, username, password, df_name, input_pg_name, output_pg_name):
        
    nto = NtoApiClient(host=host_ip, username=username, password=password, port=port, debug=True, logFile="ixvision_ztp_filter_debug.log")




# Main thread

argv = sys.argv[1:]
username = ''
password = ''
df_name = ''            # Name for Dynamic Filter to work with
network_pg_name = ''    # Name for the network port group to connect to the DF
tool_pg_name = ''       # Name for the tool port group to connect to the DF
host = ''
hosts_file = ''
config_file = ''
port = 8000

usage = 'ixvision_ztp_filter.py -u <username> -p <password> -n <dynamic_filter_name> -i <network_port_group_name> -o <tool_port_group_name> [-h <hosts> | -f <host_file>] [-r port]'

try:
    opts, args = getopt.getopt(argv,"u:p:h:f:r:n:i:o:", ["username=", "password=", "host=", "hosts_file=", "port=", "name=", "input=", "output="])
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

if df_name == '' or network_pg_name == '' or tool_pg_name == '':
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
    thread = threading.Thread(name=host, target=form_dynamic_filter, args=(host_ip, port, username, password, df_name, network_pg_name, tool_pg_name))
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




