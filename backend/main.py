"""
main.py - FastAPI application entry point (CoA Generator redesign)

Removed: APScheduler, email/SMTP routes
New: generate endpoint accepts explicit month/year/period/date_accomplished
     and streams the .xlsx file directly in the response.
"""
import os
import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List

from fastapi import (
    FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import create_tables, get_db, User, GeneratedReport
from auth import (
    get_password_hash, verify_password, create_access_token, get_current_user
)
from excel_service import generate_coa_report, build_period_info

# -------------------------
# App Init
# -------------------------
app = FastAPI(
    title="CoAutomate",
    description="CoA Report Generator",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Report-Id", "X-Filename"],
)

BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads" / "signatures"
REPORTS_DIR = BASE_DIR / "reports"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/health")
@app.get("/api/health")
def health_check():
    """Lightweight ping endpoint for uptime monitors (UptimeRobot, Cron-Job.org, etc.)"""
    return {"status": "ok"}


# -------------------------
# Startup / Shutdown
# -------------------------
@app.on_event("startup")
def startup_event():
    import logging
    logger = logging.getLogger("uvicorn")
    try:
        create_tables()
        logger.info("[STARTUP] Database tables verified/created successfully.")
    except Exception as e:
        import traceback
        logger.error(f"[STARTUP ERROR] Database connection or table creation failed: {e}")
        traceback.print_exc()


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
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerateRequest(BaseModel):
    month: int               # 1–12
    year: int                # e.g. 2026
    period: str              # "1-15" or "16-end"
    date_accomplished: str   # ISO date string, e.g. "2026-08-15"


# -------------------------
# Auth Routes
# -------------------------
@app.post("/api/auth/register", status_code=201)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


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
    import base64
    allowed_exts = {".png", ".jpg", ".jpeg"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_exts:
        raise HTTPException(status_code=400, detail="Only PNG/JPG images are allowed.")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Signature file is too large (max 2MB).")

    # 1. Save to local uploads dir for fast file streaming
    filename = f"sig_{current_user.id}{suffix}"
    dest = UPLOADS_DIR / filename
    with open(str(dest), "wb") as f:
        f.write(content)

    # 2. Save permanently into PostgreSQL as Base64 data URL
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    b64_str = f"data:{mime};base64," + base64.b64encode(content).decode("utf-8")

    current_user.signature_filename = filename
    current_user.signature_data = b64_str
    db.commit()
    db.refresh(current_user)
    return current_user


@app.get("/api/me/signature")
def get_signature(current_user: User = Depends(get_current_user)):
    import base64
    # First try serving from local disk if present
    if current_user.signature_filename:
        sig_path = UPLOADS_DIR / current_user.signature_filename
        if sig_path.exists():
            return FileResponse(str(sig_path))

    # If local disk was cleared after redeploy/restart, serve from PostgreSQL base64
    if current_user.signature_data:
        try:
            prefix, data = current_user.signature_data.split(";base64,")
            mime = prefix.replace("data:", "")
            img_bytes = base64.b64decode(data)
            # Recreate file on disk so excel_service has it
            if current_user.signature_filename:
                dest = UPLOADS_DIR / current_user.signature_filename
                dest.write_bytes(img_bytes)
            return Response(content=img_bytes, media_type=mime)
        except Exception:
            pass

    raise HTTPException(status_code=404, detail="No signature uploaded.")


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
def generate_report(
    req: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a CoA report with the user's explicit inputs.
    Saves the file to disk, logs to DB, and streams the .xlsx directly.
    The response header X-Report-Id contains the new report's DB id.
    """
    # Validate month
    if not (1 <= req.month <= 12):
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12.")

    # Parse date_accomplished
    try:
        date_acc = date.fromisoformat(req.date_accomplished)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date_accomplished format. Use YYYY-MM-DD.")

    # Validate period string
    if req.period not in ("1-15", "16-end"):
        raise HTTPException(status_code=400, detail="period must be '1-15' or '16-end'.")

    try:
        period_info = build_period_info(req.month, req.year, req.period, date_acc)
        output_path, period_info = generate_coa_report(current_user, period_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    # Log to DB
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

    # Stream the file back with the report ID in a header
    return FileResponse(
        path=str(output_path),
        filename=output_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "X-Report-Id": str(report.id),
            "X-Filename": output_path.name,
        },
    )


# -------------------------
# Serve Frontend
# -------------------------
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_frontend(full_path: str):
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>CoAutomate</h1><p>Frontend not found.</p>")
