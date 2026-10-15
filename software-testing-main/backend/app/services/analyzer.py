import json
import re
from typing import List, Dict

class OutputAnalyzer:
    @staticmethod
    def analyze_output(raw_output: str, regex_rules_json: str) -> Dict:
        findings = []
        status = "Pass"
        
        try:
            rules_config = json.loads(regex_rules_json)
            rules = rules_config.get("rules", [])
        except Exception:
            rules = []

        if not rules:
            return {"status": status, "findings": findings}

        severity_rank = {"Info": 0, "Low": 1, "Medium": 2, "Warning": 2, "High": 3, "Critical": 4}
        max_severity = -1

        lines = raw_output.split("\n")
        for line in lines:
            for rule in rules:
                pattern = rule.get("pattern")
                if pattern and re.search(pattern, line):
                    sev = rule.get("severity", "Info")
                    findings.append({
                        "severity": sev,
                        "message": rule.get("message", "Pattern matched"),
                        "recommendation": rule.get("recommendation", ""),
                        "matched_line": line.strip()
                    })
                    
                    rank = severity_rank.get(sev, 0)
                    if rank > max_severity:
                        max_severity = rank
                        if rank >= 3:
                            status = "Fail"
                        elif rank >= 1:
                            status = "Warning"
                            
        return {"status": status, "findings": findings}
