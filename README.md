# IxVision-ZTA - Zero-Touch Automation Utility for Ixia Vision Network Packet Brokers
## Overview
IxVision-ZTA is a command-line utility that helps you to apply a set of configuration steps, or actions, to an Ixia Vision Network Packet Broker (NPB). It is also capable of running discovery operations - identifying connected NPB ports, setting up proper speed and duplex parameters, parce LLDP neighbor information to identify a role of a port. When running `ixvztp`, you choose one of the actions from the following list:

* `sysinfo`  Display system information
* `portup`   Perform link status discovery for all currently disabled ports. Successfully connected ports would be configured in Network (ingress) mode.
* `lldptag`  Search for LLDP neighbor port descriptions that match one or more supplied tags. Tag the ports, connected to the matched neighbors, with corresponding keywords.
* `portmode` Set port mode to the specified value for ports that match one or more supplied tags.
* `pgform`   Form a group of ports that have keywords matching supplied tags. Both Network and Tool Port Groups are supported.
* `dfform`   Form a dynamic filter with specified input, output and filtering mode.
* `dfupdate` Update a dynamic filter with new criteria

By sequencially combining several `ixvztp` invocations, each time with a needed action, one can create a script descriping a complex configuration policy to be applied to a target NPB. 

## Installation
Prerequisites:

* OpenSSL library with TLS1.2 support
* Python 2.7
* PIP
* virtualenv - optional, used in the examples here

Create virtual environment called `ixvision` in a directory of your choice:

    export PYENV=ixvision
    virtualenv -p python2.7 $PYENV; cd $PYENV; export PYENV_DIR=`pwd`
    source "$PYENV_DIR/bin/activate"

Download VisionNPB library from GitHub (currently, IxVision-ZTA relies on 2018 version of VisionNPB library, which is available via a fork referenced below):

    cd "$PYENV_DIR"; git clone https://github.com/bortok/VisionNPB.git

Clone IxVision-ZTA repository

    git clone https://github.com/OpenIxia/ixvision-zta.git

Download pre-requisite packages:

    pip install -r ixvision-zta/requirements.txt

Test by exporting a config from an NPB, using default credentials (you might need to change those):

    WEB_API_USERNAME=admin
    WEB_API_PASSWORD=admin
    DEVICE_IP=<ip_address_of_ixia_npb>

    "$PYENV_DIR/VisionNPB/RestApi/Python/exportConfig.py" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -h $DEVICE_IP

Test by inquering system information

    "$PYENV_DIR/ixvision-zta/ixvztp" -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP sysinfo


## Usage

Initialize python environment (you might need to adopt this to your setup, depending on the directory tree structure)

    export PYENV=ixvision
    cd $PYENV; export PYENV_DIR=`pwd`
    . "$PYENV_DIR/bin/activate"
    PATH="$PYENV_DIR/ixvision-zta":$PATH

Remember to use proper credentials

    WEB_API_USERNAME=admin
    WEB_API_PASSWORD=admin
    DEVICE_IP=<ip_address_of_ixia_npb>


Perform port/link status discovery

    ixvztp -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP portup


Use LLDP neighbor information to look for TAP, SPAN or probe keywords in LLDP port descriptions and tag NPB ports with corresponding keywords. Since it takes time for LLDP neighbor database to populate, you might need to give it some time before running `lldptag` action.

    ixvztp -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP lldptag -t TAP,SPAN,probe

Create/update port groups based on keywords from the previous step. Network side - TAP ports as _**TAPs**_ port group, SPAN ports as _**SPANs**_ port group.

    ixvztp -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP pgform -t tap -n TAPs -m net
    ixvztp -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP pgform -t span -n SPANs -m net

Tool side - probe ports as _**PROBES**_ load-balancing group.

    ixvztp -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP pgform -t probe -n PROBES -m lb


Finally, connecting inputs to outputs by creating filters. Create _**AllTraffic**_ filter for traffic from _**TAPs**_ and _**SPANs**_ to _**PROBES**_ port group.

    ixvztp -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP dfform -n "AllTraffic" -i TAPs -o PROBES -m all
    ixvztp -u $WEB_API_USERNAME -p $WEB_API_PASSWORD -d $DEVICE_IP dfform -n "AllTraffic" -i SPANs -o PROBES -m all

# Copyright notice

Author: Alex Bortok (https://github.com/bortok)

COPYRIGHT 2018 - 2019 Keysight Technologies.

This code is provided under the MIT license.  
You can find the complete terms in LICENSE.txt
