"""
API endpoints for packet capture management
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path

from routers.auth_router import get_current_user
from services.packet_capture import get_packet_capture_service
from models.models import User

router = APIRouter(prefix="/api/v1/capture", tags=["packet-capture"])


class CaptureRequest(BaseModel):
    """Schema for starting packet capture"""
    interface: str = "eth0"
    capture_mode: str = "pcap"  # pcap, af_packet, af_xdp
    filter_bpf: Optional[str] = None
    duration: int = 60  # seconds
    target_ip: Optional[str] = None


class CaptureResponse(BaseModel):
    """Response for capture operations"""
    status: str
    capture_id: str
    message: str


@router.post("/start", response_model=CaptureResponse, summary="Start packet capture")
async def start_capture(
    request: CaptureRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Start a packet capture session
    
    - **interface**: Network interface to capture on (default: eth0)
    - **capture_mode**: Capture mode (pcap, af_packet, af_xdp)
    - **filter_bpf**: Optional BPF filter string
    - **duration**: Capture duration in seconds (default: 60)
    - **target_ip**: Optional target IP for focused capture
    
    Requires admin or operator role.
    """
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    service = get_packet_capture_service()
    
    try:
        if request.capture_mode == "pcap":
            capture_id = service.start_pcap_capture(
                interface=request.interface,
                filter_bpf=request.filter_bpf or "",
                duration=request.duration,
                target_ip=request.target_ip
            )
        elif request.capture_mode == "af_packet":
            capture_id = service.start_af_packet_capture(
                interface=request.interface,
                duration=request.duration
            )
        elif request.capture_mode == "af_xdp":
            capture_id = service.start_af_xdp_capture(
                interface=request.interface,
                duration=request.duration
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid capture mode: {request.capture_mode}")
        
        return CaptureResponse(
            status="success",
            capture_id=capture_id,
            message=f"Capture started with ID {capture_id}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start capture: {str(e)}")


@router.post("/stop/{capture_id}", summary="Stop packet capture")
async def stop_capture(
    capture_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Stop an ongoing packet capture
    
    - **capture_id**: Capture session ID
    
    Requires admin or operator role.
    """
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    service = get_packet_capture_service()
    
    if not service.stop_capture(capture_id):
        raise HTTPException(status_code=404, detail="Capture not found or already stopped")
    
    return {
        "status": "success",
        "message": f"Capture {capture_id} stopped"
    }


@router.get("/status/{capture_id}", summary="Get capture status")
async def get_capture_status(
    capture_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of a packet capture
    
    - **capture_id**: Capture session ID
    
    Returns capture status and file information.
    """
    service = get_packet_capture_service()
    status = service.get_capture_status(capture_id)
    
    return {
        "status": "success",
        "capture": status
    }


@router.get("/list", summary="List all captures")
async def list_captures(current_user: User = Depends(get_current_user)):
    """
    List all PCAP files
    
    Returns list of available capture files with metadata.
    """
    service = get_packet_capture_service()
    captures = service.list_captures()
    
    return {
        "status": "success",
        "captures": captures,
        "total": len(captures)
    }


@router.get("/download/{filename}", summary="Download PCAP file")
async def download_capture(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download a PCAP file
    
    - **filename**: PCAP filename
    
    Requires admin or operator role.
    """
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    service = get_packet_capture_service()
    pcap_file = service.capture_dir / filename
    
    if not pcap_file.exists() or not pcap_file.is_file():
        raise HTTPException(status_code=404, detail="PCAP file not found")
    
    # Security check: ensure file is within capture directory
    try:
        pcap_file.resolve().relative_to(service.capture_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(
        path=str(pcap_file),
        filename=filename,
        media_type="application/vnd.tcpdump.pcap"
    )


@router.delete("/cleanup", summary="Cleanup old captures")
async def cleanup_old_captures(
    max_age_days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """
    Delete old PCAP files
    
    - **max_age_days**: Maximum age in days (default: 7)
    
    Requires admin role.
    """
    if current_user.role not in ["admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    service = get_packet_capture_service()
    deleted = service.cleanup_old_captures(max_age_days)
    
    return {
        "status": "success",
        "deleted": deleted,
        "message": f"Deleted {deleted} old PCAP files"
    }
