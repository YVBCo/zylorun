import json
import re
from typing import Dict, List, Any

class OutputAnalyzer:
    @staticmethod
    def analyze_output(raw_output: str, regex_rules_json: str) -> Dict[str, Any]:
        """Analyzes command line output using pre-configured regex rules.
        Classifies status into Pass, Warning, or Fail, and aggregates findings.
        """
        findings = []
        status = "Pass"

        if not regex_rules_json:
            return {"status": status, "findings": findings}

        try:
            if isinstance(regex_rules_json, str):
                rules_config = json.loads(regex_rules_json)
            else:
                rules_config = regex_rules_json
            rules = rules_config.get("rules", []) if isinstance(rules_config, dict) else []
        except Exception:
            rules = []

        if not rules:
            return {"status": status, "findings": findings}

        severity_rank = {
            "Info": 0,
            "Low": 1,
            "Medium": 2,
            "Warning": 2,
            "High": 3,
            "Critical": 4
        }
        max_severity = -1

        lines = raw_output.split("\n")
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            for rule in rules:
                pattern = rule.get("pattern")
                if pattern and re.search(pattern, line_str, re.IGNORECASE):
                    sev = rule.get("severity", "Info")
                    findings.append({
                        "severity": sev,
                        "message": rule.get("message", "Pattern matched"),
                        "recommendation": rule.get("recommendation", "Review flagged output line."),
                        "matched_line": line_str
                    })

                    rank = severity_rank.get(sev, 0)
                    if rank > max_severity:
                        max_severity = rank
                        if rank >= 3:
                            status = "Fail"
                        elif rank >= 1 and status != "Fail":
                            status = "Warning"

        return {"status": status, "findings": findings}
