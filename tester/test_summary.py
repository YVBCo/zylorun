def generate_summary(changes, findings, previous_score, current_score):
    status_map = {"A": "adds", "M": "modifies", "D": "deletes"}
    file_actions = {}
    for c in changes:
        st = c.get("status", "M")[0]
        if st not in file_actions: file_actions[st] = []
        file_actions[st].append(c.get("file", ""))
    
    parts = []
    for st, verb in [("A", "adds"), ("M", "modifies"), ("D", "deletes"), ("R", "renames")]:
        if st in file_actions:
            if len(file_actions[st]) <= 2:
                parts.append(f"{verb} {', '.join(f'`{f}`' for f in file_actions[st])}")
            else:
                parts.append(f"{verb} {len(file_actions[st])} files")
    
    change_desc = "This commit " + ", and ".join(parts) + "." if parts else "This commit contains no detectable file changes."
    
    if previous_score is None:
        return f"{change_desc}\n\nThis is a baseline scan. All issues present in the repository at this commit are recorded as baseline. The initial score is {current_score}."
        
    new_findings = [f for f in findings if f.get("status") == "NEW"]
    resolved_findings = [f for f in findings if f.get("status") == "RESOLVED"]
    
    finding_desc = ""
    if new_findings:
        worst = max(new_findings, key=lambda x: {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(x.get("severity", ""), 0))
        issue_type = worst.get("type", "issue")
        finding_desc = f"It introduces a {worst.get('severity', 'new')} {issue_type} finding in `{worst.get('file_path')}`"
        if worst.get("line_number"): finding_desc += f" on line {worst.get('line_number')}"
        if len(new_findings) > 1: finding_desc += f", along with {len(new_findings)-1} other new issue(s)."
        else: finding_desc += "."
    elif resolved_findings:
        best = resolved_findings[0]
        finding_desc = f"It resolves a {best.get('type', 'issue')} finding in `{best.get('file_path')}`"
        if len(resolved_findings) > 1: finding_desc += f", along with {len(resolved_findings)-1} other finding(s)."
        else: finding_desc += "."
    else:
        finding_desc = "No new risk-scoring findings were introduced."
        
    score_desc = ""
    if current_score != previous_score and previous_score is not None:
        direction = "decreased" if current_score < previous_score else "improved"
        score_desc = f"As a result, the risk score {direction} from {previous_score} to {current_score}."
    else:
        score_desc = f"The score remained {current_score}."
        
    return f"{change_desc}\n\n{finding_desc} {score_desc}"

print(generate_summary([{"status": "M", "file": "test_secrets.py"}], [{"status": "NEW", "type": "Secret", "severity": "Critical", "file_path": "test_secrets.py", "line_number": 1}], 90, 40))
