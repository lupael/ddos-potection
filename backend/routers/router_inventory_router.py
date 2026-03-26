"""
Router inventory management endpoints.

Allows ISP admins/operators to register and manage their network routers,
and test connectivity via the appropriate vendor driver.
"""
import ipaddress
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from database import get_db
from models.models import Router, User
from routers.auth_router import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/routers", tags=["Router Inventory"])

_ALLOWED_VENDORS = {"cisco", "juniper", "nokia", "arista", "mikrotik"}
_ALLOWED_ROLES = {"border", "scrubbing", "access"}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class RouterCreate(BaseModel):
    """Payload for creating a new router entry."""
    name: str
    vendor: str
    ip_address: str
    port: int = 22
    username: str
    password: str
    role: str = "border"

    @field_validator("vendor")
    @classmethod
    def validate_vendor(cls, v: str) -> str:
        if v.lower() not in _ALLOWED_VENDORS:
            raise ValueError(f"vendor must be one of {sorted(_ALLOWED_VENDORS)}")
        return v.lower()

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"ip_address must be a valid IP address, got {v!r}")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v.lower() not in _ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(_ALLOWED_ROLES)}")
        return v.lower()

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v


class RouterUpdate(BaseModel):
    """Payload for updating an existing router entry."""
    name: Optional[str] = None
    vendor: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("vendor")
    @classmethod
    def validate_vendor(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in _ALLOWED_VENDORS:
            raise ValueError(f"vendor must be one of {sorted(_ALLOWED_VENDORS)}")
        return v.lower() if v else v

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError(f"ip_address must be a valid IP address, got {v!r}")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in _ALLOWED_ROLES:
            raise ValueError(f"role must be one of {sorted(_ALLOWED_ROLES)}")
        return v.lower() if v else v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v


class RouterOut(BaseModel):
    """Router response schema — never includes encrypted_password."""
    id: int
    isp_id: int
    name: str
    vendor: str
    ip_address: str
    port: int
    username: str
    role: str
    is_active: bool
    created_at: Optional[object] = None
    updated_at: Optional[object] = None

    class Config:
        from_attributes = True


class ConnectionTestResult(BaseModel):
    router_id: int
    host: str
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _encrypt_password(plaintext: str) -> str:
    """Encode the password for storage.

    WARNING: This is base64 encoding, NOT cryptographic encryption.
    Replace with a proper secrets vault (e.g., HashiCorp Vault, AWS Secrets
    Manager, or Fernet symmetric encryption) before production deployment.
    """
    import base64
    return base64.b64encode(plaintext.encode()).decode()


def _decrypt_password(encoded: str) -> str:
    import base64
    return base64.b64decode(encoded.encode()).decode()


def _require_admin_or_operator(user: User) -> None:
    if user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")


def _get_router_or_404(router_id: int, isp_id: int, db: Session) -> Router:
    obj = db.query(Router).filter(
        Router.id == router_id,
        Router.isp_id == isp_id,
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Router not found")
    return obj


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[RouterOut], summary="List routers for the caller's ISP")
def list_routers(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all routers for the authenticated ISP.

    Requires **admin** or **operator** role.
    """
    _require_admin_or_operator(current_user)
    query = db.query(Router).filter(Router.isp_id == current_user.isp_id)
    if role is not None:
        query = query.filter(Router.role == role.lower())
    if is_active is not None:
        query = query.filter(Router.is_active == is_active)
    return query.order_by(Router.name).offset(offset).limit(limit).all()


@router.post("/", response_model=RouterOut, status_code=201, summary="Add a new router")
def create_router(
    payload: RouterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a new router in the inventory.

    Requires **admin** role.
    """
    _require_admin(current_user)
    obj = Router(
        isp_id=current_user.isp_id,
        name=payload.name,
        vendor=payload.vendor,
        ip_address=payload.ip_address,
        port=payload.port,
        username=payload.username,
        encrypted_password=_encrypt_password(payload.password),
        role=payload.role,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    logger.info("Router %s (%s) added by %s", obj.name, obj.ip_address, current_user.username)
    return obj


@router.put("/{router_id}", response_model=RouterOut, summary="Update a router")
def update_router(
    router_id: int,
    payload: RouterUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing router's details.

    Requires **admin** role.
    """
    _require_admin(current_user)
    obj = _get_router_or_404(router_id, current_user.isp_id, db)
    if payload.name is not None:
        obj.name = payload.name
    if payload.vendor is not None:
        obj.vendor = payload.vendor
    if payload.ip_address is not None:
        obj.ip_address = payload.ip_address
    if payload.port is not None:
        obj.port = payload.port
    if payload.username is not None:
        obj.username = payload.username
    if payload.password is not None:
        obj.encrypted_password = _encrypt_password(payload.password)
    if payload.role is not None:
        obj.role = payload.role
    if payload.is_active is not None:
        obj.is_active = payload.is_active
    db.commit()
    db.refresh(obj)
    logger.info("Router %d updated by %s", router_id, current_user.username)
    return obj


@router.delete("/{router_id}", status_code=204, summary="Delete a router")
def delete_router(
    router_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a router from the inventory.

    Requires **admin** role.
    """
    _require_admin(current_user)
    obj = _get_router_or_404(router_id, current_user.isp_id, db)
    db.delete(obj)
    db.commit()
    logger.info("Router %d deleted by %s", router_id, current_user.username)


@router.post(
    "/{router_id}/test-connection",
    response_model=ConnectionTestResult,
    summary="Test SSH connectivity to a router",
)
def test_connection(
    router_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Attempt to connect to the router using the stored credentials.

    Requires **admin** or **operator** role.
    Returns whether the connection succeeded and a human-readable message.
    """
    _require_admin_or_operator(current_user)
    obj = _get_router_or_404(router_id, current_user.isp_id, db)

    plaintext_pw = _decrypt_password(obj.encrypted_password)
    success = False
    message = ""

    try:
        from services.router_drivers import NokiaSROSDriver, CiscoIOSDriver, JuniperDriver, AristaEOSDriver, RouterCredentials

        vendor = obj.vendor.lower()

        if vendor in ("nokia", "nokia_sros"):
            drv = NokiaSROSDriver(
                host=obj.ip_address,
                port=obj.port,
                username=obj.username,
                password=plaintext_pw,
            )
            success = drv.connect()
            message = "Connected successfully" if success else "Connection failed"

        elif vendor in ("cisco", "cisco_ios", "cisco_iosxr"):
            from services.router_drivers import _NETMIKO_AVAILABLE, ConnectHandler
            if not _NETMIKO_AVAILABLE:
                message = "netmiko not installed"
            else:
                try:
                    conn = ConnectHandler(
                        device_type="cisco_ios",
                        host=obj.ip_address,
                        username=obj.username,
                        password=plaintext_pw,
                        port=obj.port,
                    )
                    conn.disconnect()
                    success = True
                    message = "Connected successfully"
                except Exception as exc:
                    message = str(exc)

        elif vendor in ("arista", "arista_eos"):
            from services.router_drivers import _NETMIKO_AVAILABLE, ConnectHandler
            if not _NETMIKO_AVAILABLE:
                message = "netmiko not installed"
            else:
                try:
                    conn = ConnectHandler(
                        device_type="arista_eos",
                        host=obj.ip_address,
                        username=obj.username,
                        password=plaintext_pw,
                        port=obj.port,
                    )
                    conn.disconnect()
                    success = True
                    message = "Connected successfully"
                except Exception as exc:
                    message = str(exc)

        elif vendor in ("juniper", "junos"):
            from services.router_drivers import _NAPALM_AVAILABLE
            if not _NAPALM_AVAILABLE:
                message = "napalm not installed"
            else:
                import napalm  # type: ignore
                try:
                    drv_cls = napalm.get_network_driver("junos")
                    device = drv_cls(
                        hostname=obj.ip_address,
                        username=obj.username,
                        password=plaintext_pw,
                        optional_args={"port": obj.port},
                    )
                    device.open()
                    device.close()
                    success = True
                    message = "Connected successfully"
                except Exception as exc:
                    message = str(exc)

        else:
            message = f"No connection test available for vendor '{vendor}'"

    except Exception as exc:
        message = f"Unexpected error: {exc}"

    return ConnectionTestResult(
        router_id=obj.id,
        host=obj.ip_address,
        success=success,
        message=message,
    )
