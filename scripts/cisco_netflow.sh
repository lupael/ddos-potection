#!/bin/bash
# Cisco Router NetFlow Configuration Script
# This script generates Cisco IOS commands to configure NetFlow

ROUTER_IP=$1
COLLECTOR_IP=$2
COLLECTOR_PORT=${3:-2055}

if [ -z "$ROUTER_IP" ] || [ -z "$COLLECTOR_IP" ]; then
    echo "Usage: $0 <router_ip> <collector_ip> [collector_port]"
    echo "Example: $0 192.168.1.1 10.0.0.5 2055"
    exit 1
fi

echo "Generating NetFlow configuration for Cisco router $ROUTER_IP"
echo "================================================================"
echo ""
echo "Copy and paste the following commands into your Cisco router:"
echo ""
echo "! Enable NetFlow on interfaces"
echo "interface GigabitEthernet0/0"
echo "  ip flow ingress"
echo "  ip flow egress"
echo "exit"
echo ""
echo "! Configure NetFlow export"
echo "ip flow-export version 9"
echo "ip flow-export destination $COLLECTOR_IP $COLLECTOR_PORT"
echo "ip flow-export source GigabitEthernet0/0"
echo "ip flow-cache timeout active 1"
echo "ip flow-cache timeout inactive 15"
echo ""
echo "! Save configuration"
echo "write memory"
echo ""
echo "================================================================"
echo "Note: Adjust interface names according to your router configuration"
