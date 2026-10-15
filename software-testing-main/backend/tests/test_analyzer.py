import pytest
import json
from app.services.analyzer import OutputAnalyzer

def test_analyzer_pass():
    raw_output = "Nmap done: 1 IP address (1 host up) scanned in 2.5 seconds\n80/tcp closed http"
    rules = json.dumps({"rules": [
        {"pattern": ".*[0-9]+/tcp open.*", "severity": "High", "message": "Open port"}
    ]})
    
    result = OutputAnalyzer.analyze_output(raw_output, rules)
    assert result["status"] == "Pass"
    assert len(result["findings"]) == 0

def test_analyzer_fail():
    raw_output = "Nmap done: 1 IP address (1 host up) scanned in 2.5 seconds\n22/tcp open ssh"
    rules = json.dumps({"rules": [
        {"pattern": ".*[0-9]+/tcp open.*", "severity": "High", "message": "Open port found", "recommendation": "Close it"}
    ]})
    
    result = OutputAnalyzer.analyze_output(raw_output, rules)
    assert result["status"] == "Fail"
    assert len(result["findings"]) == 1
    assert result["findings"][0]["severity"] == "High"
    assert result["findings"][0]["message"] == "Open port found"
