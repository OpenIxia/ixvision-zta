# Zero-Touch Provisioning script (playbook) for a Ixia Vision NPB
# Create/update a dynamic filter between network and tool port groups 

# 1. Starting point is an Ixia Vision NPB with network and tool port groups formed
# 2. Each run of this script would configure a single dynamic filter using supplied name and filter criteria
#  - Search for an existing DF with the same name. If found with the matching type, continue by referencing that DF
#  - If not found, create a new DF
# 3. Update the DF criteria with provided rules
# 4. Search for network port group with a specified name and, if found, connect it to the input of the DF
# 5. Search for tool port group with a specified name and, if found, connect it to the output of the DF

from ixia_nto import *

from ixvision_ztp_ntolib import *

# DEFINE VARs HERE
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

def form_dynamic_filter(host_ip, port, username, password, df_name, df_input, df_output, df_mode, df_criteria = {}, use_tag_mode = False):
    
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
    
    if not use_tag_mode:
        # Search for network and tool port groups matching given names. 
        # Make sure they are not empty before connecting to filters, since ports can't be added later to an empty but connected port group
            
        ztp_df_source_port_group_id_list.extend(remove_empty_port_groups_from_id_list(nto, search_port_group_id_list(nto, {'name': df_input})))
        ztp_df_dest_port_group_id_list.extend  (remove_empty_port_groups_from_id_list(nto, search_port_group_id_list(nto, {'name': df_output})))
    
        # TODO update DF connections only if there is an actual change in list of PGs connected to it
        df_params.update({'source_port_group_list': ztp_df_source_port_group_id_list, 'dest_port_group_list': ztp_df_dest_port_group_id_list})
        nto.modifyFilter(str(ztp_df['id']), df_params)
    else:
        # Connect input ports using tags
        df_connect_via_tags(nto, str(ztp_df['id']), [df_input], 'input')
        # Connect output ports using tags
        df_connect_via_tags(nto, str(ztp_df['id']), [df_output], 'output')
