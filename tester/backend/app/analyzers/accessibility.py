"""Analyzer 9: UI/UX and Accessibility Analyzer.

Static analysis of frontend TSX, JSX, HTML, and Vue templates for WCAG 2.1 AA compliance:
- Missing alt text on images
- Missing accessible names (aria-label) on buttons and icon controls
- Missing form labels on input, select, and textarea elements
- Inaccessible interactive elements (onClick on div/span without role/tabIndex/keyboard support)
- Empty or dummy anchor links
- Missing HTML document lang attribute
"""

import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.analyzers.base import BaseAnalyzer
from app.analysis.indexer import build_repository_index


def scan_jsx_tags(content: str) -> List[Dict[str, Any]]:
    """Scans JSX/HTML tags taking into account JSX curly braces and string literals in attributes."""
    elements: List[Dict[str, Any]] = []
    n = len(content)
    i = 0
    while i < n:
        if content[i] == "<" and i + 1 < n and (content[i + 1].isalpha() or content[i + 1] in ["_"]):
            tag_start = i
            line_no = content[:tag_start].count("\n") + 1
            # Read tag name
            j = i + 1
            while j < n and (content[j].isalnum() or content[j] in ["_", "-"]):
                j += 1
            tag_name = content[i + 1 : j]

            # Now find the end of opening tag '>'
            in_quote = None
            brace_depth = 0
            k = j
            self_closing = False
            while k < n:
                ch = content[k]
                if in_quote:
                    if ch == in_quote and content[k - 1] != "\\":
                        in_quote = None
                elif ch in ['"', "'", "`"]:
                    in_quote = ch
                elif ch == "{":
                    brace_depth += 1
                elif ch == "}":
                    if brace_depth > 0:
                        brace_depth -= 1
                elif ch == ">" and brace_depth == 0 and not in_quote:
                    if k > 0 and content[k - 1] == "/":
                        self_closing = True
                    break
                k += 1

            if k < n and content[k] == ">":
                attrs = content[j : (k - 1 if self_closing else k)].strip()
                open_tag_end = k + 1
                inner = ""
                if not self_closing and tag_name.lower() not in ["img", "input", "br", "hr", "meta", "link"]:
                    # Find closing tag </tag_name>
                    closing_str = f"</{tag_name}>"
                    close_pos = content.find(closing_str, open_tag_end, min(n, open_tag_end + 2000))
                    if close_pos != -1:
                        inner = content[open_tag_end:close_pos]
                i = open_tag_end

                elements.append({
                    "tag": tag_name,
                    "attrs": attrs,
                    "self_closing": self_closing,
                    "inner": inner,
                    "line_number": line_no,
                    "raw": content[tag_start : k + 1],
                })
                continue
        i += 1
    return elements


class UiAccessibilityAnalyzer(BaseAnalyzer):
    name = "ui_accessibility"
    version = "1.0.0"
    description = "Static analysis of frontend TSX, JSX, and HTML templates for WCAG 2.1 AA accessibility."

    def _run(self, repo_dir: str, commit_sha: str, index: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        if not index:
            index = build_repository_index(repo_dir, commit_sha)

        findings: List[Dict[str, Any]] = []
        limitations: List[str] = []
        templates_scanned: List[str] = []

        total_images = 0
        total_buttons = 0
        total_inputs = 0
        total_interactive_divs = 0

        # Scan template files
        for root, dirs, fnames in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "dist", "build", "__pycache__", ".pytest_cache"]]
            for fn in fnames:
                if not fn.endswith((".tsx", ".jsx", ".html", ".vue", ".svelte")):
                    continue
                # Exclude test files
                if any(test_marker in fn.lower() for test_marker in [".test.", ".spec.", "_test."]):
                    continue

                full_p = os.path.join(root, fn)
                rel_p = os.path.relpath(full_p, repo_dir).replace("\\", "/")
                templates_scanned.append(rel_p)

                try:
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue

                file_findings, stats = self._analyze_template(content, rel_p, fn)
                findings.extend(file_findings)
                total_images += stats.get("images", 0)
                total_buttons += stats.get("buttons", 0)
                total_inputs += stats.get("inputs", 0)
                total_interactive_divs += stats.get("interactive_divs", 0)

        if not templates_scanned:
            limitations.append("No frontend template files (.tsx, .jsx, .html, .vue, .svelte) discovered.")

        limitations.append("Static AST/regex accessibility heuristics cannot evaluate dynamic runtime DOM or computed color contrast.")

        # Group by WCAG guidelines
        wcag_counts: Dict[str, int] = {}
        for f in findings:
            guideline = f.get("wcag_standard", "WCAG 2.1 AA")
            wcag_counts[guideline] = wcag_counts.get(guideline, 0) + 1

        # Calculate accessibility health score
        elements_count = total_images + total_buttons + total_inputs + total_interactive_divs
        if elements_count > 0:
            a11y_score = max(20, round(100 - (len(findings) * 50 / elements_count)))
        elif templates_scanned:
            a11y_score = 95
        else:
            a11y_score = 100

        summary = (
            f"Analyzed {len(templates_scanned)} frontend UI template(s) containing {elements_count} elements. "
            f"Identified {len(findings)} accessibility defect(s) violating WCAG 2.1 AA standards "
            f"(Accessibility Score: {a11y_score}/100)."
        )

        details = {
            "templates_scanned_count": len(templates_scanned),
            "templates_scanned": templates_scanned[:30],
            "elements_checked": {
                "images": total_images,
                "buttons": total_buttons,
                "form_inputs": total_inputs,
                "interactive_elements": total_interactive_divs,
                "total": elements_count,
            },
            "wcag_violations": wcag_counts,
            "accessibility_score": a11y_score,
            "findings_count": len(findings),
        }

        return {
            "status": "COMPLETED",
            "coverage_status": "FULL" if templates_scanned else "PARTIAL",
            "files_analyzed": len(templates_scanned),
            "summary": summary,
            "findings_count": len(findings),
            "findings": findings,
            "details": details,
            "limitations": limitations,
        }

    def _analyze_template(self, content: str, rel_path: str, filename: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Scans a single template file for WCAG accessibility violations."""
        findings: List[Dict[str, Any]] = []
        stats = {"images": 0, "buttons": 0, "inputs": 0, "interactive_divs": 0}

        # 1. Check <html lang="..."> in HTML files
        if filename.endswith(".html"):
            html_tag = re.search(r"<html([^>]*)>", content, re.IGNORECASE)
            if html_tag:
                attrs = html_tag.group(1)
                if "lang=" not in attrs.lower():
                    line_no = content[: html_tag.start()].count("\n") + 1
                    findings.append({
                        "rule_id": "A11Y-HTML-NO-LANG",
                        "category": "Accessibility",
                        "severity": "Medium",
                        "confidence": "High",
                        "classification": "Definite accessibility defect",
                        "wcag_standard": "WCAG 2.1 AA 3.1.1 Language of Page",
                        "file_path": rel_path,
                        "line_number": line_no,
                        "title": "Missing `lang` Attribute on `<html>` Tag",
                        "description": "Top-level `<html>` element does not specify a language. Screen readers cannot determine proper voice synthesis rules.",
                        "evidence": html_tag.group(0),
                        "remediation": "Add `lang=\"en\"` (or primary document language) to the `<html>` tag.",
                    })

        # Scan all JSX/HTML elements accurately
        elements = scan_jsx_tags(content)

        for el in elements:
            tag = el["tag"]
            tag_lower = tag.lower()
            attrs = el["attrs"]
            attrs_lower = attrs.lower()
            inner = el["inner"]
            line_no = el["line_number"]

            # 2. Check <img> and <Image>
            if tag_lower in ["img", "image"]:
                stats["images"] += 1
                alt_m = re.search(r"""\balt\s*=\s*(?:["']([^"']*)["']|\{([^}]+)\})""", attrs, re.IGNORECASE)
                if not alt_m:
                    findings.append({
                        "rule_id": "A11Y-IMG-NO-ALT",
                        "category": "Accessibility",
                        "severity": "High",
                        "confidence": "High",
                        "classification": "Definite accessibility defect",
                        "wcag_standard": "WCAG 2.1 AA 1.1.1 Non-text Content",
                        "file_path": rel_path,
                        "line_number": line_no,
                        "title": "Image Missing `alt` Attribute",
                        "description": "Image element lacks an `alt` attribute. Screen reader users cannot understand image content.",
                        "evidence": el["raw"][:80],
                        "remediation": "Add a descriptive `alt=\"...\"` attribute, or `alt=\"\"` with `aria-hidden=\"true\"` if purely decorative.",
                    })
                else:
                    alt_val = (alt_m.group(1) or "").strip().lower()
                    if alt_val in ["image", "picture", "photo", "img", "icon"]:
                        findings.append({
                            "rule_id": "A11Y-IMG-REDUNDANT-ALT",
                            "category": "Accessibility",
                            "severity": "Low",
                            "confidence": "High",
                            "classification": "Definite accessibility defect",
                            "wcag_standard": "WCAG 2.1 AA 1.1.1 Non-text Content",
                            "file_path": rel_path,
                            "line_number": line_no,
                            "title": f"Redundant Placeholder Alt Text: `{alt_val}`",
                            "description": f"The alt text '{alt_val}' provides no informative context to screen reader users.",
                            "evidence": el["raw"][:80],
                            "remediation": "Provide descriptive alt text describing the specific subject or function of the image.",
                        })

            # 3. Check <button> and <IconButton>
            elif tag_lower in ["button", "iconbutton"]:
                stats["buttons"] += 1
                has_visible_text = bool(re.sub(r"<[^>]+>", "", inner).strip())
                has_aria_label = any(attr in attrs_lower for attr in ["aria-label", "aria-labelledby", "title"])

                if not has_visible_text and not has_aria_label:
                    findings.append({
                        "rule_id": "A11Y-BUTTON-NO-NAME",
                        "category": "Accessibility",
                        "severity": "High",
                        "confidence": "High",
                        "classification": "Definite accessibility defect",
                        "wcag_standard": "WCAG 2.1 AA 4.1.2 Name, Role, Value",
                        "file_path": rel_path,
                        "line_number": line_no,
                        "title": "Button Missing Accessible Name (Aria-Label)",
                        "description": "Button contains only icons or no text content and does not specify `aria-label`, `aria-labelledby`, or `title`.",
                        "evidence": el["raw"][:80],
                        "remediation": "Add `aria-label=\"Descriptive action\"` to ensure assistive technologies can announce the control.",
                    })

            # 4. Check <input>, <select>, <textarea>
            elif tag_lower in ["input", "select", "textarea"]:
                if tag_lower == "input":
                    type_m = re.search(r"""\btype\s*=\s*["']([^"']+)["']""", attrs, re.IGNORECASE)
                    if type_m and type_m.group(1).lower() in ["hidden", "submit", "button", "reset"]:
                        continue

                stats["inputs"] += 1
                has_aria = any(attr in attrs_lower for attr in ["aria-label", "aria-labelledby"])
                has_id = "id=" in attrs_lower

                has_associated_label = False
                if has_id:
                    id_m = re.search(r"""\bid\s*=\s*["']([^"']+)["']""", attrs, re.IGNORECASE)
                    if id_m:
                        input_id = id_m.group(1)
                        if f'htmlFor="{input_id}"' in content or f"htmlFor='{input_id}'" in content or f'for="{input_id}"' in content:
                            has_associated_label = True

                if not has_aria and not has_associated_label:
                    findings.append({
                        "rule_id": "A11Y-FORM-INPUT-NO-LABEL",
                        "category": "Accessibility",
                        "severity": "High",
                        "confidence": "Medium",
                        "classification": "Valid heuristic finding requiring manual verification",
                        "wcag_standard": "WCAG 2.1 AA 1.3.1 Info and Relationships & 3.3.2 Labels or Instructions",
                        "file_path": rel_path,
                        "line_number": line_no,
                        "title": f"Form Control `<{tag}>` Missing Accessible Label",
                        "description": (
                            f"Form input `<{tag}>` has neither an associated `<label htmlFor=\"...\">` "
                            f"nor an `aria-label` / `aria-labelledby` attribute."
                        ),
                        "evidence": el["raw"][:80],
                        "remediation": f"Associate with a `<label htmlFor=\"id\">` or add `aria-label=\"Field name\"` directly on `<{tag}>`.",
                    })

            # 5. Check Inaccessible Interactive Elements (div, span, p, a with onClick)
            elif "onclick" in attrs_lower:
                stats["interactive_divs"] += 1

                if tag_lower in ["div", "span", "p"]:
                    has_role = "role=" in attrs_lower
                    has_tabindex = "tabindex" in attrs_lower
                    has_keydown = any(k in attrs_lower for k in ["onkeydown", "onkeyup", "onkeypress"])

                    if not has_role or not has_tabindex or not has_keydown:
                        findings.append({
                            "rule_id": "A11Y-INTERACTIVE-ELEMENT",
                            "category": "Accessibility",
                            "severity": "Medium",
                            "confidence": "High",
                            "classification": "Definite keyboard accessibility defect",
                            "wcag_standard": "WCAG 2.1 AA 2.1.1 Keyboard Accessible",
                            "file_path": rel_path,
                            "line_number": line_no,
                            "title": f"Non-Semantic Clickable `<{tag}>` Lacks Keyboard Support",
                            "description": (
                                f"Element `<{tag}>` has an `onClick` handler but lacks `role=\"button\"`, `tabIndex={{0}}`, "
                                f"or keyboard event handlers (onKeyDown). Keyboard-only users cannot activate this element."
                            ),
                            "evidence": el["raw"][:80],
                            "remediation": f"Replace `<{tag}>` with a native `<button>` element, or add `role=\"button\"`, `tabIndex={{0}}`, and `onKeyDown`.",
                        })

                elif tag_lower == "a":
                    href_m = re.search(r"""\bhref\s*=\s*["']([^"']*)["']""", attrs, re.IGNORECASE)
                    if href_m and href_m.group(1).strip() in ["#", "", "javascript:void(0)", "javascript:void(0);"]:
                        findings.append({
                            "rule_id": "A11Y-DUMMY-ANCHOR",
                            "category": "Accessibility",
                            "severity": "Low",
                            "confidence": "High",
                            "classification": "Definite semantic defect",
                            "wcag_standard": "WCAG 2.1 AA 2.4.4 Link Purpose",
                            "file_path": rel_path,
                            "line_number": line_no,
                            "title": "Dummy Anchor Link `href=\"#\"` Used as Button",
                            "description": "Anchor tag uses a dummy `href=\"#\"` with an `onClick` handler instead of a semantic `<button>`.",
                            "evidence": el["raw"][:80],
                            "remediation": "Replace `<a href=\"#\">` with a semantic `<button>` element.",
                        })

        return findings, stats
