from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
from fpdf2 import FPDF
import csv
import os

from database import get_db
from models.models import Report, User, Alert, TrafficLog, MitigationAction
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

def generate_pdf_report(isp_name, report_type, start_date, end_date, stats_data, filepath):
    """Generate PDF report"""
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "DDoS Protection Platform Report", ln=True, align="C")
    pdf.ln(5)
    
    # ISP Info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"ISP: {isp_name}", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Report Type: {report_type.capitalize()}", ln=True)
    pdf.cell(0, 8, f"Period: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(10)
    
    # Summary Statistics
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Summary Statistics", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Total Alerts: {stats_data['alerts_count']}", ln=True)
    pdf.cell(0, 8, f"Critical Alerts: {stats_data['critical_alerts']}", ln=True)
    pdf.cell(0, 8, f"High Severity Alerts: {stats_data['high_alerts']}", ln=True)
    pdf.cell(0, 8, f"Total Packets Processed: {stats_data['total_packets']:,}", ln=True)
    
    # Safe division for bytes to GB conversion
    total_gb = (stats_data['total_bytes'] / (1024**3)) if stats_data['total_bytes'] > 0 else 0
    pdf.cell(0, 8, f"Total Bytes: {stats_data['total_bytes']:,} ({total_gb:.2f} GB)", ln=True)
    pdf.cell(0, 8, f"Mitigation Actions Taken: {stats_data['mitigation_count']}", ln=True)
    pdf.ln(10)
    
    # Alert Breakdown
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Alert Breakdown by Type", ln=True)
    pdf.set_font("Arial", "", 10)
    for alert_type, count in stats_data['alerts_by_type'].items():
        pdf.cell(0, 8, f"  {alert_type}: {count}", ln=True)
    pdf.ln(5)
    
    # Recommendations
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Recommendations", ln=True)
    pdf.set_font("Arial", "", 10)
    if stats_data['critical_alerts'] > 10:
        pdf.cell(0, 8, "- Consider upgrading to a higher protection tier", ln=True)
    if stats_data['total_packets'] > 1000000:
        pdf.cell(0, 8, "- High traffic volume detected - ensure adequate capacity", ln=True)
    pdf.cell(0, 8, "- Regular review of mitigation rules recommended", ln=True)
    
    pdf.output(filepath)

def generate_csv_report(report_type, start_date, end_date, stats_data, alerts, filepath):
    """Generate CSV report"""
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Header
        writer.writerow(['DDoS Protection Platform Report'])
        writer.writerow(['Report Type', report_type])
        writer.writerow(['Period Start', start_date.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['Period End', end_date.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Summary Statistics'])
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Alerts', stats_data['alerts_count']])
        writer.writerow(['Critical Alerts', stats_data['critical_alerts']])
        writer.writerow(['High Severity Alerts', stats_data['high_alerts']])
        writer.writerow(['Total Packets', stats_data['total_packets']])
        writer.writerow(['Total Bytes', stats_data['total_bytes']])
        writer.writerow(['Mitigation Actions', stats_data['mitigation_count']])
        writer.writerow([])
        
        # Alert Details
        writer.writerow(['Alert Details'])
        writer.writerow(['ID', 'Type', 'Severity', 'Source IP', 'Target IP', 'Status', 'Created At'])
        for alert in alerts:
            writer.writerow([
                alert.id,
                alert.alert_type,
                alert.severity,
                alert.source_ip,
                alert.target_ip,
                alert.status,
                alert.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])

@router.post("/generate")
async def generate_report(
    report_type: str = "monthly",
    file_format: str = "pdf",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a new report (admin only)"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Validate format
    if file_format not in ["pdf", "csv", "txt"]:
        raise HTTPException(status_code=400, detail="Invalid file format. Use pdf, csv, or txt")
    
    # Calculate period based on report type
    end_date = datetime.utcnow()
    if report_type == "monthly":
        start_date = end_date - timedelta(days=30)
    elif report_type == "weekly":
        start_date = end_date - timedelta(days=7)
    else:
        start_date = end_date - timedelta(days=1)
    
    # Gather comprehensive report data
    from sqlalchemy import func
    
    # Get ISP info
    from models.models import ISP
    isp = db.query(ISP).filter(ISP.id == current_user.isp_id).first()
    
    # Alert statistics
    alerts_count = db.query(func.count(Alert.id)).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.created_at >= start_date
    ).scalar()
    
    critical_alerts = db.query(func.count(Alert.id)).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.severity == "critical",
        Alert.created_at >= start_date
    ).scalar()
    
    high_alerts = db.query(func.count(Alert.id)).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.severity == "high",
        Alert.created_at >= start_date
    ).scalar()
    
    # Alert breakdown by type
    alerts_by_type = db.query(
        Alert.alert_type,
        func.count(Alert.id).label('count')
    ).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.created_at >= start_date
    ).group_by(Alert.alert_type).all()
    
    alerts_by_type_dict = {alert_type: count for alert_type, count in alerts_by_type}
    
    # Traffic statistics
    traffic_stats = db.query(
        func.sum(TrafficLog.packets).label("total_packets"),
        func.sum(TrafficLog.bytes).label("total_bytes")
    ).filter(
        TrafficLog.isp_id == current_user.isp_id,
        TrafficLog.timestamp >= start_date
    ).first()
    
    # Mitigation statistics
    mitigation_count = db.query(func.count(MitigationAction.id)).filter(
        MitigationAction.created_at >= start_date
    ).scalar()
    
    # Get recent alerts for CSV
    recent_alerts = db.query(Alert).filter(
        Alert.isp_id == current_user.isp_id,
        Alert.created_at >= start_date
    ).order_by(Alert.created_at.desc()).limit(100).all()
    
    stats_data = {
        'alerts_count': alerts_count,
        'critical_alerts': critical_alerts,
        'high_alerts': high_alerts,
        'total_packets': traffic_stats.total_packets or 0,
        'total_bytes': traffic_stats.total_bytes or 0,
        'mitigation_count': mitigation_count,
        'alerts_by_type': alerts_by_type_dict
    }
    
    # Generate report file
    report_dir = os.environ.get('REPORTS_DIR', '/tmp/reports')
    os.makedirs(report_dir, exist_ok=True)
    
    filename = f"report_{current_user.isp_id}_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_format}"
    filepath = os.path.join(report_dir, filename)
    
    # Generate based on format
    if file_format == "pdf":
        generate_pdf_report(isp.name, report_type, start_date, end_date, stats_data, filepath)
    elif file_format == "csv":
        generate_csv_report(report_type, start_date, end_date, stats_data, recent_alerts, filepath)
    else:  # txt
        with open(filepath, "w") as f:
            f.write(f"DDoS Protection Platform Report\n")
            f.write(f"================================\n\n")
            f.write(f"ISP: {isp.name}\n")
            f.write(f"Report Type: {report_type}\n")
            f.write(f"Period: {start_date} to {end_date}\n\n")
            f.write(f"Statistics:\n")
            f.write(f"- Total Alerts: {alerts_count}\n")
            f.write(f"- Critical Alerts: {critical_alerts}\n")
            f.write(f"- High Severity Alerts: {high_alerts}\n")
            f.write(f"- Total Packets: {traffic_stats.total_packets or 0}\n")
            f.write(f"- Total Bytes: {traffic_stats.total_bytes or 0}\n")
            f.write(f"- Mitigation Actions: {mitigation_count}\n")
    
    # Save report record
    db_report = Report(
        isp_id=current_user.isp_id,
        report_type=report_type,
        period_start=start_date,
        period_end=end_date,
        file_path=filepath,
        file_format=file_format
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    
    return {"message": "Report generated successfully", "report_id": db_report.id, "format": file_format}

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
