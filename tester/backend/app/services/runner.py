import asyncio
import json
import re
import subprocess
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database.models import RunHistory, CommandConfig, Target
from app.services.analyzer import OutputAnalyzer

# RFC-compliant hostname, IPv4, IPv6, or localhost
HOST_REGEX = re.compile(
    r'^(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}|(?:\d{1,3}\.){3}\d{1,3}|\[?[0-9a-fA-F:]+\]?|localhost)$'
)

# Approved executable allowlist to prevent arbitrary system execution
APPROVED_EXECUTABLES = {
    "ping", "ping.exe",
    "curl", "curl.exe",
    "nmap", "nmap.exe",
    "python", "python.exe",
    "node", "node.exe",
    "eslint", "eslint.cmd",
    "git", "git.exe",
    "openssl", "openssl.exe"
}

class CommandRunner:
    @staticmethod
    def validate_target_host(host: str) -> bool:
        if not host or len(host) > 255:
            return False
        # Remove any protocol prefix for validation
        clean_host = host.split("://")[-1].split("/")[0].split(":")[0]
        return bool(HOST_REGEX.match(clean_host))

    @staticmethod
    async def run_command_stream(
        run_id: int,
        command_config: CommandConfig,
        target: Target,
        args: List[str],
        db: Session,
        websocket=None
    ) -> RunHistory:
        db_run = db.query(RunHistory).filter(RunHistory.id == run_id).first()
        if not db_run:
            raise ValueError(f"RunHistory record {run_id} not found.")

        db_run.status = "Running"
        db.commit()

        # Security check 1: Target host validation
        if not CommandRunner.validate_target_host(target.host):
            db_run.status = "Error"
            db_run.raw_output = f"[SECURITY REJECTION] Target host '{target.host}' failed validation. Refusing execution."
            db_run.findings = json.dumps([{"severity": "Critical", "message": "Invalid or dangerous target host."}])
            db_run.end_time = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            if websocket:
                await websocket.send_json({"error": "Invalid target host pattern", "status": "Error"})
                await websocket.close()
            return db_run

        # Security check 2: Executable check
        executable_base = command_config.executable.lower().split("/")[-1].split("\\")[-1]
        if executable_base not in APPROVED_EXECUTABLES:
            db_run.status = "Error"
            db_run.raw_output = f"[SECURITY REJECTION] Executable '{command_config.executable}' is not in the approved security tools allowlist."
            db_run.findings = json.dumps([{"severity": "Critical", "message": "Unauthorized executable."}])
            db_run.end_time = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            if websocket:
                await websocket.send_json({"error": "Unauthorized executable", "status": "Error"})
                await websocket.close()
            return db_run

        # Security check 3: Argument allowlist validation
        try:
            allowed_args_list = json.loads(command_config.allowed_args) if isinstance(command_config.allowed_args, str) else command_config.allowed_args
        except Exception:
            allowed_args_list = []

        validated_args = []
        for arg in args:
            if arg in allowed_args_list:
                validated_args.append(arg)
            else:
                db_run.status = "Error"
                db_run.raw_output = f"[SECURITY REJECTION] Disallowed argument '{arg}' was supplied for tool '{command_config.name}'."
                db_run.findings = json.dumps([{"severity": "High", "message": f"Disallowed argument: {arg}"}])
                db_run.end_time = datetime.now(timezone.utc).replace(tzinfo=None)
                db.commit()
                if websocket:
                    await websocket.send_json({"error": f"Disallowed argument: {arg}", "status": "Error"})
                    await websocket.close()
                return db_run

        clean_host = target.host.split("://")[-1].split("/")[0]
        cmd_args = [command_config.executable] + validated_args + [clean_host]
        full_output = []

        process = None
        try:
            # shell=False strictly enforced
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=False
            )

            loop = asyncio.get_running_loop()

            async def read_stream_async():
                while True:
                    line = await loop.run_in_executor(None, process.stdout.readline)
                    if not line:
                        break
                    decoded_line = line.strip()
                    full_output.append(decoded_line)
                    if websocket:
                        try:
                            await websocket.send_json({"stream": "stdout", "data": decoded_line})
                        except Exception:
                            pass

            timeout_sec = min(max(command_config.timeout_seconds, 5), 300)
            await asyncio.wait_for(read_stream_async(), timeout=timeout_sec)
            exit_code = await loop.run_in_executor(None, process.wait)

            raw_output_str = "\n".join(full_output)
            db_run.raw_output = raw_output_str

            if exit_code != 0:
                analysis = OutputAnalyzer.analyze_output(raw_output_str, command_config.regex_rules)
                db_run.status = "Fail" if analysis["findings"] else "Error"
                findings = analysis["findings"] or [{"severity": "Warning", "message": f"Process exited with non-zero code {exit_code}."}]
                db_run.findings = json.dumps(findings)
            else:
                analysis = OutputAnalyzer.analyze_output(raw_output_str, command_config.regex_rules)
                db_run.status = analysis["status"]
                db_run.findings = json.dumps(analysis["findings"])

        except asyncio.TimeoutError:
            if process:
                process.kill()
            db_run.status = "Timeout"
            full_output.append("[TIMEOUT] Process killed after exceeding timeout limit.")
            db_run.raw_output = "\n".join(full_output)
            db_run.findings = json.dumps([{"severity": "High", "message": "Command execution timed out."}])
        except Exception as e:
            if process:
                process.kill()
            db_run.status = "Fail"
            full_output.append(f"[EXCEPTION] {repr(e)}")
            db_run.raw_output = "\n".join(full_output)
            db_run.findings = json.dumps([{"severity": "Critical", "message": f"Execution error: {str(e)}"}])
        finally:
            db_run.end_time = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()

            if websocket:
                try:
                    await websocket.send_json({
                        "status": db_run.status,
                        "exit_code": process.returncode if process else -1
                    })
                    await websocket.close()
                except Exception:
                    pass

        return db_run
