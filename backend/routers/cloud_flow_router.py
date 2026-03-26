"""
Cloud VPC Flow Log upload router.

Accepts AWS and GCP VPC Flow Log uploads, parses them, and returns a
normalised flow summary.  All endpoints are ISP-scoped via JWT.
"""
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from models.models import User
from routers.auth_router import get_current_user
from services.cloud_flow_ingestion import AWSVPCFlowParser, GCPFlowParser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/cloud-flows", tags=["Cloud Flow Ingestion"])


@router.post("/aws/upload")
async def upload_aws_flow_log(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Parse an AWS VPC Flow Log file and return a summary.

    Accepts a multipart file upload containing an AWS VPC Flow Log in the
    standard space-separated text format.

    Returns:
        JSON with ``isp_id``, ``flow_count``, ``accepted``, ``rejected``,
        ``protocols``, and ``flows`` (the first 100 normalised records).
    """
    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not decode file: {exc}") from exc

    parser = AWSVPCFlowParser()
    flows = parser.parse_file(content)

    accepted = sum(1 for f in flows if f.get("action") == "ACCEPT")
    rejected = sum(1 for f in flows if f.get("action") == "REJECT")
    protocols: dict[str, int] = {}
    for flow in flows:
        proto = flow.get("protocol", "unknown")
        protocols[proto] = protocols.get(proto, 0) + 1

    return {
        "isp_id": current_user.isp_id,
        "flow_count": len(flows),
        "accepted": accepted,
        "rejected": rejected,
        "protocols": protocols,
        "flows": flows[:100],
    }


@router.post("/gcp/upload")
async def upload_gcp_flow_log(
    payload: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Parse GCP VPC Flow Log records and return a summary.

    Request body:
    ```json
    {"records": [ <GCP flow log JSON record>, … ]}
    ```

    Returns:
        JSON with ``isp_id``, ``flow_count``, ``protocols``, and ``flows``
        (the first 100 normalised records).
    """
    records: List[dict] = payload.get("records", [])
    if not isinstance(records, list):
        raise HTTPException(status_code=422, detail="'records' must be a list")

    parser = GCPFlowParser()
    flows = []
    for r in records:
        flow = parser.parse_record(r)
        if flow is not None:
            flows.append(flow)

    protocols: dict[str, int] = {}
    for flow in flows:
        proto = flow.get("protocol", "unknown")
        protocols[proto] = protocols.get(proto, 0) + 1

    return {
        "isp_id": current_user.isp_id,
        "flow_count": len(flows),
        "protocols": protocols,
        "flows": flows[:100],
    }
