from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import RunHistory
import csv
import io
import json

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{run_id}/json")
def get_report_json(run_id: int, db: Session = Depends(get_db)):
    run = db.query(RunHistory).filter(RunHistory.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    return {
        "run_id": run.id,
        "status": run.status,
        "start_time": run.start_time.isoformat() if run.start_time else None,
        "end_time": run.end_time.isoformat() if run.end_time else None,
        "findings": json.loads(run.findings) if run.findings else []
    }

@router.get("/{run_id}/csv")
def get_report_csv(run_id: int, db: Session = Depends(get_db)):
    run = db.query(RunHistory).filter(RunHistory.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    findings = json.loads(run.findings) if run.findings else []
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Severity", "Message", "Recommendation", "Matched Line"])
    
    for f in findings:
        writer.writerow([f.get("severity", ""), f.get("message", ""), f.get("recommendation", ""), f.get("matched_line", "")])
        
    return PlainTextResponse(output.getvalue(), media_type="text/csv")
