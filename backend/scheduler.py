"""
scheduler.py - APScheduler cron jobs for automatic CoA generation and emailing
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date
from sqlalchemy.orm import Session
from database import SessionLocal, User, GeneratedReport
from excel_service import generate_coa_report
from email_service import send_coa_email

scheduler = BackgroundScheduler()


def run_coa_generation(trigger_day: int):
    """
    Called on the 1st or 16th of the month.
    Generates CoA reports for all active users and emails them.
    """
    today = date.today()
    # Force the day to match the scheduled trigger
    trigger_date = today.replace(day=trigger_day)

    print(f"[SCHEDULER] Running CoA generation for trigger date: {trigger_date}")

    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        print(f"[SCHEDULER] Found {len(users)} active users.")

        for user in users:
            try:
                output_path, period_info = generate_coa_report(user, trigger_date)
                print(f"[SCHEDULER] Generated report: {output_path.name}")

                # Log to DB
                report = GeneratedReport(
                    user_id=user.id,
                    period=period_info["period"],
                    month=period_info["month_name"],
                    year=period_info["year"],
                    filename=output_path.name,
                    email_sent=False,
                )
                db.add(report)
                db.commit()
                db.refresh(report)

                # Send email
                sent = send_coa_email(
                    recipient_email=user.email,
                    recipient_name=user.full_name,
                    period_label=period_info["period"],
                    month_name=period_info["month_name"],
                    year=period_info["year"],
                    attachment_path=output_path,
                )
                if sent:
                    report.email_sent = True
                    db.commit()

            except Exception as e:
                print(f"[SCHEDULER] Error for user {user.email}: {e}")

    finally:
        db.close()


def start_scheduler():
    """Register cron jobs and start the scheduler."""

    # Every 16th at 00:01 AM → report for period 1-15
    scheduler.add_job(
        lambda: run_coa_generation(16),
        CronTrigger(day=16, hour=0, minute=1),
        id="coa_1_15",
        name="CoA Period 1-15 Generator",
        replace_existing=True,
    )

    # Every 1st at 00:01 AM → report for period 16-end of previous month
    scheduler.add_job(
        lambda: run_coa_generation(1),
        CronTrigger(day=1, hour=0, minute=1),
        id="coa_16_31",
        name="CoA Period 16-31 Generator",
        replace_existing=True,
    )

    scheduler.start()
    print("[SCHEDULER] Started. Jobs: CoA 1-15 (16th) and CoA 16-31 (1st).")
    return scheduler


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("[SCHEDULER] Stopped.")
