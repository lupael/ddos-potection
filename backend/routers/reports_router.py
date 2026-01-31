from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta

from database import get_db
from models.models import Report, User, Alert, TrafficLog
from routers.auth_router import get_current_user

router = APIRouter()

class ReportResponse(BaseModel):
    id: int
    report_type: str
    period_start: datetime
    period_end: datetime
    file_path: str
    created_at: datetime
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all reports for the ISP"""
    reports = db.query(Report).filter(
        Report.isp_id == current_user.isp_id
    ).order_by(Report.created_at.desc()).all()
    return reports

@router.post("/generate")
async def generate_report(
    report_type: str = "monthly",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new report (admin only)"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Calculate period based on report type
    end_date = datetime.utcnow()
    if report_type == "monthly":
        start_date = end_date - timedelta(days=30)
    elif report_type == "weekly":
        start_date = end_date - timedelta(days=7)
    else:
        start_date = end_date - timedelta(days=1)
    
    # Gather report data
    from sqlalchemy import func
    
    alerts_count = db.query(func.count(Alert.id)).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.created_at >= start_date
    ).scalar()
    
    traffic_stats = db.query(
        func.sum(TrafficLog.packets).label("total_packets"),
        func.sum(TrafficLog.bytes).label("total_bytes")
    ).filter(
        TrafficLog.isp_id == current_user.isp_id,
        TrafficLog.timestamp >= start_date
    ).first()
    
    # Generate PDF report (simplified)
    import os
    report_dir = "/tmp/reports"
    os.makedirs(report_dir, exist_ok=True)
    
    filename = f"report_{current_user.isp_id}_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = os.path.join(report_dir, filename)
    
    with open(filepath, "w") as f:
        f.write(f"DDoS Protection Platform Report\n")
        f.write(f"================================\n\n")
        f.write(f"Report Type: {report_type}\n")
        f.write(f"Period: {start_date} to {end_date}\n\n")
        f.write(f"Statistics:\n")
        f.write(f"- Total Alerts: {alerts_count}\n")
        f.write(f"- Total Packets: {traffic_stats.total_packets or 0}\n")
        f.write(f"- Total Bytes: {traffic_stats.total_bytes or 0}\n")
    
    # Save report record
    db_report = Report(
        isp_id=current_user.isp_id,
        report_type=report_type,
        period_start=start_date,
        period_end=end_date,
        file_path=filepath
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    return {"message": "Report generated successfully", "report_id": db_report.id}

@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a report file"""
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.isp_id == current_user.isp_id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    import os
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(
        report.file_path,
        media_type="application/octet-stream",
        filename=os.path.basename(report.file_path)
    )
