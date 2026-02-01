"""
API endpoints for hostgroup and threshold management
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from routers.auth_router import get_current_user
from services.hostgroup_manager import get_hostgroup_manager
from models.models import User

router = APIRouter(prefix="/api/v1/hostgroups", tags=["hostgroups"])


class HostGroupCreate(BaseModel):
    """Schema for creating a hostgroup"""
    name: str
    subnet: str  # CIDR format, e.g., "192.168.1.0/24"
    thresholds: Dict[str, int]  # e.g., {"packets_per_second": 10000, "bytes_per_second": 100000000}
    scripts: Optional[Dict[str, str]] = None  # e.g., {"block": "/path/to/block.sh", "notify": "/path/to/notify.sh"}


class HostGroupUpdate(BaseModel):
    """Schema for updating a hostgroup"""
    thresholds: Optional[Dict[str, int]] = None
    scripts: Optional[Dict[str, str]] = None


class IPCheckRequest(BaseModel):
    """Schema for checking IP thresholds"""
    ip: str


@router.post("/", summary="Create hostgroup")
async def create_hostgroup(
    hostgroup: HostGroupCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new hostgroup with custom thresholds
    
    - **name**: Unique hostgroup name
    - **subnet**: CIDR subnet (e.g., "192.168.1.0/24")
    - **thresholds**: Threshold configuration (packets_per_second, bytes_per_second, flows_per_second)
    - **scripts**: Optional block/notify scripts
    
    Requires admin role.
    """
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    manager = get_hostgroup_manager()
    
    success = manager.add_hostgroup(
        name=hostgroup.name,
        subnet=hostgroup.subnet,
        thresholds=hostgroup.thresholds,
        scripts=hostgroup.scripts
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to create hostgroup. Check if name is unique and subnet is valid.")
    
    return {
        "status": "success",
        "message": f"Hostgroup {hostgroup.name} created",
        "hostgroup": manager.hostgroups[hostgroup.name].to_dict()
    }


@router.get("/", summary="List all hostgroups")
async def list_hostgroups(current_user: User = Depends(get_current_user)):
    """
    List all configured hostgroups
    
    Returns list of hostgroups with their configurations.
    """
    manager = get_hostgroup_manager()
    return {
        "status": "success",
        "hostgroups": manager.list_hostgroups()
    }


@router.get("/{name}", summary="Get hostgroup details")
async def get_hostgroup(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific hostgroup
    
    - **name**: Hostgroup name
    """
    manager = get_hostgroup_manager()
    
    if name not in manager.hostgroups:
        raise HTTPException(status_code=404, detail="Hostgroup not found")
    
    return {
        "status": "success",
        "hostgroup": manager.hostgroups[name].to_dict()
    }


@router.delete("/{name}", summary="Delete hostgroup")
async def delete_hostgroup(
    name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a hostgroup
    
    - **name**: Hostgroup name
    
    Requires admin role.
    """
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    manager = get_hostgroup_manager()
    
    if not manager.remove_hostgroup(name):
        raise HTTPException(status_code=404, detail="Hostgroup not found")
    
    return {
        "status": "success",
        "message": f"Hostgroup {name} deleted"
    }


@router.post("/check-ip", summary="Check IP thresholds")
async def check_ip_thresholds(
    request: IPCheckRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Check which thresholds apply to a specific IP
    
    - **ip**: IP address to check
    
    Returns the applicable hostgroup and thresholds.
    """
    manager = get_hostgroup_manager()
    
    hostgroup = manager.get_hostgroup_for_ip(request.ip)
    thresholds = manager.get_thresholds_for_ip(request.ip)
    
    return {
        "status": "success",
        "ip": request.ip,
        "hostgroup": hostgroup.to_dict() if hostgroup else None,
        "thresholds": thresholds
    }


@router.get("/defaults/thresholds", summary="Get default thresholds")
async def get_default_thresholds(current_user: User = Depends(get_current_user)):
    """
    Get default thresholds used when no hostgroup matches
    
    Returns the system default threshold configuration.
    """
    manager = get_hostgroup_manager()
    
    return {
        "status": "success",
        "default_thresholds": manager.default_thresholds
    }
