#!/usr/bin/env python3
"""
Example script demonstrating BGP Blackholing (RTBH) usage
See docs/BGP-RTBH.md for complete setup instructions
"""
import requests
import time
import argparse
from typing import Optional

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"


class BGPBlackholeClient:
    """Client for triggering BGP blackhole mitigations"""
    
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def login(self, username: str, password: str) -> str:
        """Login and get JWT token"""
        response = requests.post(
            f"{self.api_url}/auth/token",
            data={
                "username": username,
                "password": password
            }
        )
        
        if response.status_code == 200:
            token = response.json()["access_token"]
            self.headers["Authorization"] = f"Bearer {token}"
            print(f"✓ Logged in as {username}")
            return token
        else:
            raise Exception(f"Login failed: {response.text}")
    
    def trigger_blackhole(self, alert_id: int, ip_address: str, 
                         reason: str = "DDoS attack") -> Optional[int]:
        """Trigger BGP blackhole for an IP address
        
        Args:
            alert_id: ID of the alert triggering this mitigation
            ip_address: IP address to blackhole (will be converted to /32)
            reason: Reason for blackholing
        
        Returns:
            Mitigation ID if successful, None otherwise
        """
        prefix = f"{ip_address}/32"
        
        print(f"🚫 Triggering BGP blackhole for {prefix}...")
        
        # Create mitigation action
        response = requests.post(
            f"{self.api_url}/mitigations/",
            headers=self.headers,
            json={
                "alert_id": alert_id,
                "action_type": "bgp_blackhole",
                "details": {
                    "prefix": prefix,
                    "reason": reason
                }
            }
        )
        
        if response.status_code != 200:
            print(f"✗ Failed to create mitigation: {response.text}")
            return None
        
        mitigation_id = response.json()["id"]
        print(f"✓ Mitigation created (ID: {mitigation_id})")
        
        # Execute the mitigation
        exec_response = requests.post(
            f"{self.api_url}/mitigations/{mitigation_id}/execute",
            headers=self.headers
        )
        
        if exec_response.status_code == 200:
            print(f"✓ BGP blackhole active for {prefix}")
            print(f"  → Route announced with next-hop 192.0.2.1")
            print(f"  → Community tag: 65535:666")
            return mitigation_id
        else:
            print(f"✗ Failed to execute mitigation: {exec_response.text}")
            return None
    
    def withdraw_blackhole(self, mitigation_id: int) -> bool:
        """Withdraw BGP blackhole
        
        Args:
            mitigation_id: ID of the mitigation to stop
        
        Returns:
            True if successful, False otherwise
        """
        print(f"🔓 Withdrawing BGP blackhole (ID: {mitigation_id})...")
        
        response = requests.post(
            f"{self.api_url}/mitigations/{mitigation_id}/stop",
            headers=self.headers
        )
        
        if response.status_code == 200:
            print(f"✓ BGP blackhole withdrawn")
            return True
        else:
            print(f"✗ Failed to withdraw blackhole: {response.text}")
            return False
    
    def list_active_blackholes(self):
        """List all active BGP blackhole mitigations"""
        print("📋 Active BGP blackholes:")
        
        response = requests.get(
            f"{self.api_url}/mitigations/",
            headers=self.headers
        )
        
        if response.status_code == 200:
            mitigations = response.json()
            
            active_blackholes = [
                m for m in mitigations 
                if m["action_type"] == "bgp_blackhole" and m["status"] == "active"
            ]
            
            if not active_blackholes:
                print("  No active blackholes")
                return
            
            for m in active_blackholes:
                prefix = m["details"].get("prefix", "unknown")
                created = m["created_at"]
                print(f"  • ID {m['id']}: {prefix} (since {created})")
        else:
            print(f"✗ Failed to list mitigations: {response.text}")


def main():
    parser = argparse.ArgumentParser(
        description="BGP Blackholing (RTBH) Example Script"
    )
    parser.add_argument("action", choices=["trigger", "withdraw", "list"],
                       help="Action to perform")
    parser.add_argument("--username", default="admin",
                       help="API username (default: admin)")
    parser.add_argument("--password", default="password",
                       help="API password")
    parser.add_argument("--api-url", default=API_BASE_URL,
                       help=f"API base URL (default: {API_BASE_URL})")
    parser.add_argument("--alert-id", type=int, default=1,
                       help="Alert ID (for trigger action)")
    parser.add_argument("--ip", help="IP address to blackhole (for trigger action)")
    parser.add_argument("--mitigation-id", type=int,
                       help="Mitigation ID (for withdraw action)")
    parser.add_argument("--duration", type=int, default=0,
                       help="Automatically withdraw after N seconds (0 = manual)")
    
    args = parser.parse_args()
    
    # Create client
    client = BGPBlackholeClient(args.api_url, "")
    
    # Login
    try:
        client.login(args.username, args.password)
    except Exception as e:
        print(f"✗ {e}")
        return 1
    
    # Perform action
    if args.action == "trigger":
        if not args.ip:
            print("✗ --ip is required for trigger action")
            return 1
        
        mitigation_id = client.trigger_blackhole(
            args.alert_id,
            args.ip,
            "Manual blackhole via script"
        )
        
        if mitigation_id and args.duration > 0:
            print(f"⏱  Will automatically withdraw after {args.duration} seconds")
            time.sleep(args.duration)
            client.withdraw_blackhole(mitigation_id)
    
    elif args.action == "withdraw":
        if not args.mitigation_id:
            print("✗ --mitigation-id is required for withdraw action")
            return 1
        
        client.withdraw_blackhole(args.mitigation_id)
    
    elif args.action == "list":
        client.list_active_blackholes()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
