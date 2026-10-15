import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models import RunHistory, User
from app.auth.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{run_id}/json")
async def get_report_json(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RunHistory).where(RunHistory.id == run_id, RunHistory.user_id == current_user.id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    findings = json.loads(run.findings) if run.findings else []
    return {
        "run_id": run.id,
        "command_id": run.command_id,
        "target_id": run.target_id,
        "status": run.status,
        "start_time": run.start_time,
        "end_time": run.end_time,
        "findings": findings
    }

@router.get("/{run_id}/csv")
async def get_report_csv(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(RunHistory).where(RunHistory.id == run_id, RunHistory.user_id == current_user.id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    findings = json.loads(run.findings) if run.findings else []
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Severity", "Message", "Recommendation", "Matched Line"])

    for f in findings:
        writer.writerow([
            f.get("severity", "Info"),
            f.get("message", ""),
            f.get("recommendation", ""),
            f.get("matched_line", "")
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=security_scan_run_{run_id}.csv"}
    )
