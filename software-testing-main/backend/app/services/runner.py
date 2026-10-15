import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import RunHistory, CommandConfig, Target
from app.services.analyzer import OutputAnalyzer

class CommandRunner:
    @staticmethod
    async def run_command_stream(
        run_id: int,
        command_config: CommandConfig,
        target: Target,
        args: list[str],
        db: Session,
        websocket=None
    ):
        db_run = db.query(RunHistory).filter(RunHistory.id == run_id).first()
        db_run.status = "Running"
        db.commit()

        cmd_args = [command_config.executable] + args + [target.host]
        full_output = []
        
        try:
            import subprocess
            import threading
            
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            def read_stream():
                for line in process.stdout:
                    decoded_line = line.strip()
                    full_output.append(decoded_line)
                    if websocket:
                        try:
                            # We must send sync, but we are in a thread. 
                            # Since websocket is async, we can use asyncio.run_coroutine_threadsafe
                            # Or just run it synchronously if possible.
                            pass
                        except Exception:
                            pass

            # Since websocket.send_json is async and we need to stream it,
            # it's better to read from the sync process.stdout using asyncio loop in an executor.
            
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
                            
            await asyncio.wait_for(
                read_stream_async(),
                timeout=command_config.timeout_seconds
            )
            
            # Wait for process to finish
            exit_code = await loop.run_in_executor(None, process.wait)
            
            raw_output_str = "\n".join(full_output)
            db_run.raw_output = raw_output_str
            
            if exit_code != 0:
                db_run.status = "Error"
                db_run.findings = json.dumps([{"severity": "Critical", "message": "Command exited with non-zero code."}])
            else:
                analysis = OutputAnalyzer.analyze_output(raw_output_str, command_config.regex_rules)
                db_run.status = analysis["status"]
                db_run.findings = json.dumps(analysis["findings"])
            
        except asyncio.TimeoutError:
            if process:
                process.kill()
            db_run.status = "Timeout"
            full_output.append("Process killed due to timeout.")
            db_run.raw_output = "\n".join(full_output)
        except Exception as e:
            db_run.status = "Fail"
            full_output.append(repr(e))
            db_run.raw_output = "\n".join(full_output)
        
        db_run.end_time = datetime.now(timezone.utc)
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
