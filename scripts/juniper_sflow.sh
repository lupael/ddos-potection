#!/bin/bash
# Juniper Router sFlow Configuration Script
# Generates Juniper JUNOS commands to configure sFlow

ROUTER_IP=$1
COLLECTOR_IP=$2
COLLECTOR_PORT=${3:-6343}
SAMPLING_RATE=${4:-1000}

if [ -z "$ROUTER_IP" ] || [ -z "$COLLECTOR_IP" ]; then
    echo "Usage: $0 <router_ip> <collector_ip> [collector_port] [sampling_rate]"
    echo "Example: $0 192.168.1.1 10.0.0.5 6343 1000"
    exit 1
fi

echo "Generating sFlow configuration for Juniper router $ROUTER_IP"
echo "================================================================"
echo ""
echo "Copy and paste the following commands into your Juniper router:"
echo ""
echo "# Enter configuration mode"
echo "configure"
echo ""
echo "# Configure sFlow"
echo "set protocols sflow collector $COLLECTOR_IP udp-port $COLLECTOR_PORT"
echo "set protocols sflow interfaces all"
echo "set protocols sflow sample-rate ingress $SAMPLING_RATE"
echo "set protocols sflow sample-rate egress $SAMPLING_RATE"
echo "set protocols sflow polling-interval 20"
echo "set protocols sflow source-ip <router-management-ip>"
echo ""
echo "# Commit configuration"
echo "commit and-quit"
echo ""
echo "================================================================"
echo "Note: Replace <router-management-ip> with your router's management IP"
