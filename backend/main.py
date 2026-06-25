"""
main.py - FastAPI application entry point
"""
import os
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import (
    FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import create_tables, get_db, User, GeneratedReport
from auth import (
    get_password_hash, verify_password, create_access_token, get_current_user
)
from excel_service import generate_coa_report
from email_service import send_coa_email
from scheduler import start_scheduler, stop_scheduler

# -------------------------
# App Init
# -------------------------
app = FastAPI(
    title="CoAutomate",
    description="Automated CoA Report Generation System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads" / "signatures"
REPORTS_DIR = BASE_DIR / "reports"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# -------------------------
# Startup / Shutdown
# -------------------------
@app.on_event("startup")
def startup_event():
    create_tables()
    start_scheduler()


@app.on_event("shutdown")
def shutdown_event():
    stop_scheduler()


# -------------------------
# Pydantic Schemas
# -------------------------
class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    department: str
    college: str
    total_teaching_load: str
    term_school_year: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    college: Optional[str] = None
    total_teaching_load: Optional[str] = None
    term_school_year: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    department: str
    college: str
    total_teaching_load: str
    term_school_year: str
    signature_filename: Optional[str]

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    id: int
    period: str
    month: str
    year: int
    filename: str
    email_sent: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SmtpConfig(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_name: str


# -------------------------
# Auth Routes
# -------------------------
@app.post("/api/auth/register", status_code=201)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        department=user_data.department,
        college=user_data.college,
        total_teaching_load=user_data.total_teaching_load,
        term_school_year=user_data.term_school_year,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token = create_access_token({"sub": new_user.email})
    return {"access_token": token, "token_type": "bearer", "user": UserResponse.from_orm(new_user)}


@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "user": UserResponse.from_orm(user)}


# -------------------------
# User Profile Routes
# -------------------------
@app.get("/api/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@app.patch("/api/me", response_model=UserResponse)
def update_profile(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in update.dict(exclude_none=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@app.post("/api/me/signature", response_model=UserResponse)
async def upload_signature(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed_exts = {".png", ".jpg", ".jpeg"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_exts:
        raise HTTPException(status_code=400, detail="Only PNG/JPG images are allowed.")

    filename = f"sig_{current_user.id}{suffix}"
    dest = UPLOADS_DIR / filename

    with open(str(dest), "wb") as f:
        shutil.copyfileobj(file.file, f)

    current_user.signature_filename = filename
    db.commit()
    db.refresh(current_user)
    return current_user


@app.get("/api/me/signature")
def get_signature(current_user: User = Depends(get_current_user)):
    if not current_user.signature_filename:
        raise HTTPException(status_code=404, detail="No signature uploaded.")
    sig_path = UPLOADS_DIR / current_user.signature_filename
    if not sig_path.exists():
        raise HTTPException(status_code=404, detail="Signature file not found.")
    return FileResponse(str(sig_path))


# -------------------------
# Report Routes
# -------------------------
@app.get("/api/reports", response_model=List[ReportResponse])
def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = (
        db.query(GeneratedReport)
        .filter(GeneratedReport.user_id == current_user.id)
        .order_by(GeneratedReport.created_at.desc())
        .all()
    )
    return reports


@app.get("/api/reports/{report_id}/download")
def download_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    file_path = REPORTS_DIR / str(current_user.id) / report.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found on disk.")

    return FileResponse(
        path=str(file_path),
        filename=report.filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.delete("/api/reports/{report_id}", status_code=204)
def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    # Delete the file from disk if it exists
    file_path = REPORTS_DIR / str(current_user.id) / report.filename
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass

    db.delete(report)
    db.commit()
    return None


@app.post("/api/reports/generate")
def manual_generate(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually triggers a CoA generation for the current period."""
    today = date.today()
    # Determine trigger: if day >= 16, use 16th; else use 1st
    if today.day >= 16:
        trigger_date = today.replace(day=16)
    else:
        trigger_date = today.replace(day=1)

    try:
        output_path, period_info = generate_coa_report(current_user, trigger_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    report = GeneratedReport(
        user_id=current_user.id,
        period=period_info["period"],
        month=period_info["month_name"],
        year=period_info["year"],
        filename=output_path.name,
        email_sent=False,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "message": "Report generated successfully.",
        "report": ReportResponse.from_orm(report),
    }


@app.post("/api/reports/{report_id}/send-email")
def resend_report_email(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(GeneratedReport).filter(
        GeneratedReport.id == report_id,
        GeneratedReport.user_id == current_user.id,
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    file_path = REPORTS_DIR / str(current_user.id) / report.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found on disk.")

    sent = send_coa_email(
        recipient_email=current_user.email,
        recipient_name=current_user.full_name,
        period_label=report.period,
        month_name=report.month,
        year=report.year,
        attachment_path=file_path,
    )
    if sent:
        report.email_sent = True
        db.commit()
        return {"message": "Email sent successfully."}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email. Check SMTP settings.")


# -------------------------
# SMTP Settings (per-user config stored in config)
# -------------------------
@app.post("/api/settings/smtp")
def configure_smtp(config: SmtpConfig, current_user: User = Depends(get_current_user)):
    """Update SMTP settings."""
    from config import save_smtp_config
    cfg = {
        "smtp_host": config.smtp_host,
        "smtp_port": config.smtp_port,
        "smtp_username": config.smtp_username,
        "smtp_password": config.smtp_password,
        "smtp_from_name": config.smtp_from_name
    }
    save_smtp_config(cfg)
    
    # Reload email_service globals
    import email_service
    email_service.SMTP_HOST = config.smtp_host
    email_service.SMTP_PORT = config.smtp_port
    email_service.SMTP_USERNAME = config.smtp_username
    email_service.SMTP_PASSWORD = config.smtp_password
    email_service.SMTP_FROM_NAME = config.smtp_from_name
    email_service.SMTP_FROM_EMAIL = config.smtp_username
    return {"message": "SMTP settings updated."}


@app.get("/api/settings/smtp-status")
def smtp_status(current_user: User = Depends(get_current_user)):
    import email_service
    return {
        "configured": bool(email_service.SMTP_USERNAME and email_service.SMTP_PASSWORD),
        "smtp_host": email_service.SMTP_HOST,
        "smtp_port": email_service.SMTP_PORT,
        "smtp_username": email_service.SMTP_USERNAME,
        "smtp_password": email_service.SMTP_PASSWORD,
        "smtp_from_name": email_service.SMTP_FROM_NAME
    }


# -------------------------
# Serve Frontend
# -------------------------
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_frontend(full_path: str):
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>CoAutomate</h1><p>Frontend not found.</p>")
