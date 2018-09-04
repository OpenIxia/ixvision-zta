#!/usr/bin/env python
#
# Zero-Touch Provisioning script for a Ixia Vision NPB

import sys
import argparse
import threading
import json

from ixvision_ztp_lldp_tag import *
from ixvision_ztp_port_group import *
from ixvision_ztp_filter import *

# DEFINE GLOBAL VARs HERE

debug_on = False

# Possible actions and usage arguments help sting
ztp_actions_choices = {'portup': 'port status discovery', \
                        'lldptag': 'lldp-based port tagging', \
                        'pgform' : 'port group formation', \
                        'dfform' : 'dynamic filter formation'}

ztp_actions_usage = {'portup': '[-k <keyword>]', \
                        'lldptag': '-t <tag1>,<tag2>,...', \
                        'pgform' : '-t <tag1>,<tag2>,... -n <port_group_name> -m net|lb', \
                        'dfform' : '-n <dynamic_filter_name> -i <network_port_group_name> -o <tool_port_group_name> -m all|none|pbc|dbc|pbcu|dbcm -c <filter_criteria_file>'}

# DEFINE GLOBAL FUNCTIONS HERE

# ****************************************************************************************** #
# Main thread

# CLI arguments parser
parser = argparse.ArgumentParser(prog='ixvztp.py', description='Zero-Touch Provisioning script for a Ixia Vision NPB.')
parser.add_argument('-u', '--username', required=True)
parser.add_argument('-p', '--password', required=True)
parser.add_argument('-d', '--hostname', required=True)
parser.add_argument('-r', '--port', default='8000')


subparsers = parser.add_subparsers(dest='subparser_name')
portup_parser = subparsers.add_parser('portup', description=ztp_actions_choices['portup'])
portup_parser.add_argument('-k', '--keyword')

lldptag_parser = subparsers.add_parser('lldptag', description=ztp_actions_choices['lldptag'])
lldptag_parser.add_argument('-t', '--tag', required=True)

pgform_parser = subparsers.add_parser('pgform', description=ztp_actions_choices['pgform'])
pgform_parser.add_argument('-t', '--tag', required=True)
pgform_parser.add_argument('-n', '--name', required=True)
pgform_parser.add_argument('-m', '--mode', required=True, choices=pg_modes_supported.keys())

dfform_parser = subparsers.add_parser('dfform', description=ztp_actions_choices['dfform'])
dfform_parser.add_argument('-n', '--name', required=True)
dfform_parser.add_argument('-i', '--input', required=True)
dfform_parser.add_argument('-o', '--output', required=True)
dfform_parser.add_argument('-m', '--mode', required=True, choices=df_modes_supported.keys())
dfform_parser.add_argument('-c', '--criteria')


# Common parameters
args = parser.parse_args()

if debug_on:
    print ('DEBUG: argumens %s' % args)

username = args.username
password = args.password
host = args.hostname
port = args.port


if args.subparser_name in ztp_actions_choices:
    print ('Starting %s for %s' % (ztp_actions_choices[args.subparser_name], host))
    if args.subparser_name == 'lldptag':
        # Task-specific parameters
        tags = args.tag.split(",")          # A list of keywords to match LLDP info againts
        
        tag_ports(host, port, username, password, tags)
        
    elif args.subparser_name == 'pgform':
        # Task-specific parameters
        tags = args.tag.upper().split(",")  # A list of keywords to match port keywords info againts. NTO keywords are always in upper case
        port_group_name = args.name         # Name for the group to use (in order to avoid referencing automatically generated group number)
        port_group_mode = args.mode         # (net) for NETWORK, (lb) for LOAD_BALANCE - no other modes are supported yet
        
        form_port_groups(host, port, username, password, tags, port_group_name, port_group_mode)
        
    elif args.subparser_name == 'dfform':
        # Task-specific parameters
        df_name = args.name             # Name for Dynamic Filter to work with
        network_pg_name = args.input    # Name for the network port group to connect to the DF
        tool_pg_name = args.output      # Name for the tool port group to connect to the DF
        df_mode = args.mode             # Mode for Dynamic Filter
        criteria_file = args.criteria   # File with dynamic filter criteria in JSON format
        df_criteria = None              # Criteria for Dynamic Filter after pasing criteria_file

        if df_criteria_required(df_mode):
            if criteria_file == None:
                print ("Error: criteria file is requied for dynamic filter mode %s" % (df_mode))
                sys.exit(2)
            else:
                parse_failed = False
                try:
                    with open(criteria_file) as f:
                        try:
                            df_criteria = json.load(f)
                            print("Filter criteria has been loaded from %s" % criteria_file)
                        except:
                            print("Error: can't parse filter criteria from %s" % criteria_file)
                            parse_failed = True
                            sys.exit(2)
                except:
                    if not parse_failed:
                        print("Error: can't read filter criteria from %s" % criteria_file)
                    sys.exit(2)
        form_dynamic_filter(host, port, username, password, df_name, network_pg_name, tool_pg_name, df_mode, df_criteria)
    else:
        print ('Unsupported action %s' % args.subparser_name)
        sys.exit(2)
else:
    parser.usage()
    sys.exit(2)





