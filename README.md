# Zero-Touch Provisioning for Ixia Vision NPBs
Example of post-discovery initialization script.
Environment vars required:
~~~~
DEVICE_IP - IP address of a Vision NPB
WEB_API_USERNAME - username to use for REST API
WEB_API_PASSWORD - password to use for REST API
LLDP_DELAY - delay in seconds to wait before starting LLDP discovery
~~~~

~~~~
echo "Discovered a $DEVICE_TYPE device with a management IP address $DEVICE_IP - initializing ZTP"

# Initialize python environment
export PYENV=ixvision
cd $PYENV; export PYENV_DIR=`pwd`
. "$PYENV_DIR/bin/activate"

# Launch ZTP - port inventory
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP portup

# Hold on for LLDP to kick in
echo "Pausing for $LLDP_DELAY seconds for LLDP neighbors to be learned"
sleep $LLDP_DELAY

# Launch LLDP port discovery - look for TAP,SPAN,monitor keywords in LLDP port descriptions
echo "Run port discovery via LLDP for the following keywords: TAP,SPAN,monitor"
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP lldptag -t TAP,SPAN,bro-monitor,moloch-capture

# Create/update port groups based on discovered port tags

# Network side - TAP and SPAN ports as TAPs IPG
echo "Create/update network port group TAPs with ports tagged as TAP"
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP pgform -t tap -n TAPs -m net
echo "Create/update network port group SPANs with ports tagged as SPAN"
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP pgform -t span -n SPANs -m net

# Tool side - monitor ports as BRO LBG
echo "Create/update load-balance tool port group BRO with ports tagged as monitor"
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP pgform -t bro-monitor -n BRO -m lb

echo "Create/update load-balance tool port group MOLOCH with ports tagged as capture"
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP pgform -t moloch-capture -n MOLOCH -m lb


# TODO Enable LLDP TX from Tool ports

# Create filters
echo "Create IoC_Detection filter for traffic from TAPs"
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP dfform -n "IoC_Detection" -i TAPs -o BRO -m all
echo "Connect IoC_Detection filter to SPANs as well"
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP dfform -n "IoC_Detection" -i SPANs -o BRO  -m all

echo "Create IPv4_Capture filter for traffic from TAPs"
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP dfform -n "Traffic_Capture" -i TAPs -o MOLOCH -m pbc -c moloch-ipv4.json
echo "Connect IPv4_Capture filter to SPANs as well"
"$PYENV_DIR/ixvision-ztp/ixvztp.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP dfform -n "Traffic_Capture" -i SPANs -o MOLOCH -m pbc -c moloch-ipv4.json

~~~~

