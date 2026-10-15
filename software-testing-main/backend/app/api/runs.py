from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import RunHistory, CommandConfig, Target
from app.services.runner import CommandRunner
from app.services.analyzer import OutputAnalyzer
import json
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/runs", tags=["runs"])

class ManualLogRequest(BaseModel):
    log_text: str

@router.post("/analyze-manual")
def analyze_manual_log(req: ManualLogRequest):
    lines = req.log_text.replace("\r", "").split("\n")
    findings = []
    status = "Pass"
    current_file = "Unknown File"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        line_lower = line.lower()
        
        # Detect file paths or zip file headers
        if line.startswith("--- File:") or line.startswith("C:\\") or line.startswith("/") or line.endswith(".js") or line.endswith(".jsx"):
            current_file = line.replace("--- File: ", "").replace(" ---", "")
            continue
            
        is_critical = any(k in line_lower for k in ["error", "fail", "secret", "password", "token", "leak", "xss", "rce", "vulnerab", "danger"])
        is_warning = any(k in line_lower for k in ["warning", "security", "disclosure", "sast", "sca", "header", "leftover"])
        
        if is_critical:
            findings.append({
                "severity": "Critical",
                "message": f"{current_file} -> {line}",
                "recommendation": "Critical issue detected. Review immediately."
            })
            status = "Fail"
        elif is_warning:
            findings.append({
                "severity": "Warning",
                "message": f"{current_file} -> {line}",
                "recommendation": "Security warning or best practice violation."
            })
            if status == "Pass":
                status = "Warning"
                
    # We removed the inline Gemini call to make the analysis 100x faster!
    # Instead, we just use ultra-fast local logic, and the user can click "Generate AI Prompt" for AI fixes.
    for finding in findings:
        msg = finding["message"].lower()
        
        # Extract just the filename from the path
        file_path = finding["message"].split(" -> ")[0]
        file_name = file_path.split("\\")[-1].split("/")[-1]
        
        if "identifier directly after number" in msg:
            finding["recommendation"] = f"This syntax error occurs in '{file_name}' when a number is placed directly adjacent to a variable or string identifier without spacing. JavaScript engines cannot parse this because it blurs the line between a numeric literal and a variable name. To fix this, you should either add a space to separate the two tokens, or wrap the text in quotation marks if it is meant to be a string."
        elif "unexpected token <" in msg:
            finding["recommendation"] = f"This error occurs because standard ESLint or Node parsers do not natively understand React JSX syntax (like <div>) found in '{file_name}'. When the parser encounters the < symbol, it expects valid JavaScript, not HTML-like tags. To resolve this, you must install and configure a JSX-compatible parser plugin, such as @babel/eslint-parser, in your configuration."
        elif "empty block statement" in msg:
            finding["recommendation"] = f"An empty block statement has been detected in '{file_name}', meaning there are curly braces {{}} containing no executable code. Leaving blocks empty can confuse future developers, hide logical flaws, or indicate incomplete features. It is recommended to either remove the empty block entirely or add a comment explaining why it has been intentionally left blank."
        elif "never used" in msg:
            finding["recommendation"] = f"A variable has been initialized or declared within '{file_name}' but is never referenced or utilized anywhere else in the code. Unused variables consume memory unnecessarily, increase bundle sizes, and clutter the codebase. You should either remove the variable entirely or, if it is required for an API signature, prefix it with an underscore."
        elif "non literal argument" in msg:
            finding["recommendation"] = f"A severe security vulnerability (Path Traversal) may exist in '{file_name}' because a dynamic, user-controlled variable is being passed into a file system function like fs.readFile. If attackers inject paths like ../../etc/passwd, they could access highly sensitive system files. Always strictly validate and restrict input paths to a dedicated safe directory."
        elif "object injection" in msg:
            finding["recommendation"] = f"This represents a potential Prototype Pollution or Object Injection vulnerability in '{file_name}'. When object properties are accessed using dynamic, user-supplied keys, attackers can overwrite internal prototypes, potentially leading to remote code execution. Ensure you freeze critical objects, use Map structures, or strictly validate keys."
        elif "globalthis" in msg:
            finding["recommendation"] = f"The code in '{file_name}' attempts to use globalThis, which is a modern JavaScript feature that provides a standard way to access the global object. However, your current linting setup is configured for an older version of ECMAScript that does not recognize it. To resolve this error, update your configuration environment settings to explicitly support es2020 or higher."
        elif "secret" in msg or "password" in msg:
            finding["recommendation"] = f"Extremely critical security risk: Hardcoded credentials, secrets, or passwords have been detected in '{file_name}'. Exposing sensitive tokens in your repository files allows anyone with access to completely compromise your systems or data. You must immediately revoke the compromised secret and ensure it is never committed to version control. Instead, store it securely in a secrets manager or environment variable."
        elif "xss" in msg or "rce" in msg:
            finding["recommendation"] = f"A potentially dangerous function capable of executing Cross-Site Scripting (XSS) or Remote Code Execution (RCE) was found in '{file_name}'. Using functions like eval() allows attackers to run malicious scripts inside your application if the input is not perfectly sanitized. You must rigorously sanitize all data using a dedicated library, or rewrite the logic."
        else:
            finding["recommendation"] = f"An anomalous issue or vulnerability pattern was detected within '{file_name}' that requires your manual review. Due to the unique nature of this finding, automated static analysis could not classify the exact root cause. Please closely inspect the flagged line of code, or simply click the 'Generate AI Prompt' button below for a comprehensive fix."
                
    return {"status": status, "findings": findings}

class GenerateFixRequest(BaseModel):
    findings: Optional[list] = []
    custom_prompt: Optional[str] = None

@router.post("/generate-fix")
def generate_comprehensive_fix(req: GenerateFixRequest):
    import os
    import requests
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key or gemini_key == "your_api_key_here":
        return {"response": "No valid Gemini API key found in the backend .env file. Please add one to use this feature!"}
        
    if req.custom_prompt and req.custom_prompt.strip():
        prompt = req.custom_prompt.strip()
    else:
        prompt = "I have the following errors in my codebase that I need help fixing:\n\n"
        for f in (req.findings or []):
            prompt += f"Error: {f.get('message')}\n"
        prompt += "\nPlease provide the exact code required to fix these issues. Format your response clearly in Markdown."
    
    models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]
    last_error = "Unknown Error"
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        try:
            res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            data = res.json()
            if "error" in data:
                last_error = data["error"].get("message", "Unknown Error")
                continue
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {"response": text}
        except Exception as e:
            last_error = str(e)
            continue
            
    return {"response": f"Gemini API Error: {last_error}"}

@router.websocket("/ws/{command_id}/{target_id}")
async def websocket_run(websocket: WebSocket, command_id: int, target_id: int, db: Session = Depends(get_db)):
    await websocket.accept()
    
    command = db.query(CommandConfig).filter(CommandConfig.id == command_id).first()
    target = db.query(Target).filter(Target.id == target_id).first()
    
    if not command or not target:
        await websocket.send_json({"error": "Command or Target not found"})
        await websocket.close()
        return
        
    new_run = RunHistory(
        command_id=command.id,
        target_id=target.id,
        user_id=1, # Mock user_id for now
        status="Pending"
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    
    try:
        data = await websocket.receive_text()
        args = json.loads(data).get("args", [])
    except WebSocketDisconnect:
        return
    except Exception:
        args = []

    allowed = json.loads(command.allowed_args)
    for arg in args:
        if arg not in allowed:
                await websocket.send_json({"error": f"Disallowed argument: {arg}"})
                await websocket.close()
                return
                
    await CommandRunner.run_command_stream(new_run.id, command, target, args, db, websocket)

@router.get("/")
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(RunHistory).all()
    return runs

class UrlSpeedTestRequest(BaseModel):
    url: str

@router.post("/url-speed-test")
def analyze_url_speed(req: UrlSpeedTestRequest):
    import time, requests
    url = req.url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    headers = {
        "User-Agent": "SecRunner-SpeedAudit/2.0 (compatible; Security-Performance-Bot)"
    }
    
    start_time = time.perf_counter()
    try:
        response = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        total_time_ms = round((time.perf_counter() - start_time) * 1000)
        ttfb_ms = round(response.elapsed.total_seconds() * 1000)
        content_size_bytes = len(response.content)
        status_code = response.status_code
        
        # Color coding: Green (< 400ms), Yellow (400ms - 900ms), Red (> 900ms or 4xx/5xx)
        if total_time_ms < 400 and status_code < 400:
            speed_grade = "GREEN"
            status_text = "Fast / Optimal Performance"
            badge_color = "#00e676"
        elif total_time_ms <= 900 and status_code < 400:
            speed_grade = "YELLOW"
            status_text = "Moderate / Average Response"
            badge_color = "#ffab00"
        else:
            speed_grade = "RED"
            status_text = "Slow / High Latency"
            badge_color = "#ff3366"

        return {
            "success": True,
            "url": url,
            "status_code": status_code,
            "total_time_ms": total_time_ms,
            "ttfb_ms": ttfb_ms,
            "content_size_bytes": content_size_bytes,
            "speed_grade": speed_grade,
            "status_text": status_text,
            "badge_color": badge_color,
            "server": response.headers.get("Server", "Unknown"),
            "content_type": response.headers.get("Content-Type", "Unknown"),
            "encoding": response.headers.get("Content-Encoding", "None"),
            "redirects": len(response.history)
        }
    except Exception as e:
        total_time_ms = round((time.perf_counter() - start_time) * 1000)
        return {
            "success": False,
            "url": url,
            "status_code": 0,
            "total_time_ms": total_time_ms,
            "ttfb_ms": total_time_ms,
            "content_size_bytes": 0,
            "speed_grade": "RED",
            "status_text": f"Connection Failed ({str(e)})",
            "badge_color": "#ff3366",
            "server": "N/A",
            "content_type": "N/A",
            "encoding": "N/A",
            "redirects": 0
        }

