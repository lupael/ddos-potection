#!/usr/bin/env python3
"""
MikroTik Router Integration Script
Configures NetFlow export on MikroTik routers

Requirements:
    pip install routeros-api
"""

import sys

def configure_netflow(router_ip, username, password, collector_ip, collector_port=2055):
    """Configure NetFlow on MikroTik router"""
    try:
        # Import here to provide clear error message
        try:
            from routeros_api import RouterOsApiPool
        except ImportError:
            print("Error: routeros-api library not installed")
            print("Please install it with: pip install routeros-api")
            return False
        
        # Connect to router
        connection = RouterOsApiPool(
            router_ip,
            username=username,
            password=password,
            plaintext_login=True
        )
        
        api = connection.get_api()
        
        # Configure NetFlow
        traffic_flow = api.get_resource('/ip/traffic-flow')
        
        # Enable traffic flow
        traffic_flow.set(
            id='*1',
            enabled='yes',
            interfaces='all'
        )
        
        # Add collector
        target = api.get_resource('/ip/traffic-flow/target')
        target.add(
            address=f'{collector_ip}:{collector_port}',
            version='9'
        )
        
        print(f"✓ NetFlow configured successfully on {router_ip}")
        print(f"  - Collector: {collector_ip}:{collector_port}")
        print(f"  - Version: NetFlow v9")
        
        connection.disconnect()
        return True
        
    except Exception as e:
        print(f"✗ Error configuring MikroTik router: {e}")
        return False

def main():
    if len(sys.argv) < 5:
        print("Usage: python mikrotik_integration.py <router_ip> <username> <password> <collector_ip> [collector_port]")
        print("Example: python mikrotik_integration.py 192.168.1.1 admin password 10.0.0.5 2055")
        sys.exit(1)
    
    router_ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    collector_ip = sys.argv[4]
    collector_port = int(sys.argv[5]) if len(sys.argv) > 5 else 2055
    
    print(f"Configuring MikroTik router {router_ip}...")
    configure_netflow(router_ip, username, password, collector_ip, collector_port)

if __name__ == "__main__":
    main()
