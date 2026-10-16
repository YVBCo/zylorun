import os
import sys
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

def clean_xml(text):
    """Sanitize XML entities for ReportLab Paragraphs while allowing bold/italic/br tags."""
    # First protect allowed tags
    text = text.replace("<b>", "___B_START___").replace("</b>", "___B_END___")
    text = text.replace("<i>", "___I_START___").replace("</i>", "___I_END___")
    text = text.replace("<br>", "___BR___").replace("<br/>", "___BR___")
    # Escape raw xml characters
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Restore allowed tags
    text = text.replace("___B_START___", "<b>").replace("___B_END___", "</b>")
    text = text.replace("___I_START___", "<i>").replace("___I_END___", "</i>")
    text = text.replace("___BR___", "<br/>")
    return text

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "GitFlow / VovaSec — Plain English Guide: Assurance & Project Hub")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
        
        # Footer
        self.setFont("Helvetica", 8)
        self.drawString(54, 35, "Vovalyx Technologies • Confidential Platform Documentation")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 35, page_str)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 558, 46)
        self.restoreState()

def create_guide_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#087CFF")
    dark_color = colors.HexColor("#0F172A")
    body_color = colors.HexColor("#334155")
    card_bg = colors.HexColor("#F8FAFC")
    border_color = colors.HexColor("#E2E8F0")
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=dark_color,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=12
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=dark_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=body_color,
        spaceAfter=3
    )

    example_style = ParagraphStyle(
        'Example_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0369A1"),
        spaceAfter=2
    )

    story = []

    # Title Block
    story.append(Paragraph("Platform Architecture & Feature Guide", title_style))
    story.append(Paragraph("Simple Explanations and Real-World Examples for System Assurance (35 Tests) & Project Hub (9 Modules)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=12))

    intro_p = Paragraph(
        clean_xml("<b>Welcome to the GitFlow / VovaSec Platform Guide.</b> This document explains every single test and module inside your software in plain English. No heavy jargon—just clear explanations, real-world examples, and what happens behind the scenes."),
        body_style
    )
    story.append(intro_p)
    story.append(Spacer(1, 8))

    # ==========================================
    # PART 1: 35 SYSTEM ASSURANCE TESTS
    # ==========================================
    story.append(Paragraph("PART 1: The 35 System Assurance Tests", h1_style))
    story.append(Paragraph(
        clean_xml("The <b>System Assurance Suite</b> checks if your application is healthy, secure, and crash-proof. It runs all 35 tests in less than <b>20 milliseconds</b>."),
        body_style
    ))
    story.append(Spacer(1, 6))

    assurance_data = [
        # 1. Chaos & Resilience
        ("1. Chaos & State Resilience", [
            ("Test 1: Process Interruption Recovery",
             "Tests if the software recovers smoothly if a worker process crashes or gets killed midway.",
             "Imagine a chef dropping a pan. Instead of setting the kitchen on fire, they clean up the spill, turn off the burner, and restart the recipe safely."),
            ("Test 2: Network Jitter & Drop Resilience",
             "Tests what happens when internet connection fluctuates, stutters, or drops packets.",
             "Like listening to music on the radio inside a tunnel. If signal drops, it pauses politely and reconnects without crashing your car's radio.")
        ]),

        # 2. Container & Docker
        ("2. Container & Docker Security", [
            ("Test 3: Docker Privilege Isolation Check",
             "Verifies containers cannot access the underlying master host operating system.",
             "Like staying in a hotel room. You have a key for your bedroom, but you are not allowed inside the master breaker electrical room."),
            ("Test 4: Non-Root User Runtime Audit",
             "Ensures the app runs as a normal worker, not as a superuser administrator.",
             "You don't give master administrative passwords to temporary contractors; they only get access to the specific tools they need.")
        ]),

        # 3. Cloud & IAM
        ("3. Cloud Security & IAM Posture", [
            ("Test 5: Cloud IaC Misconfiguration Scanner",
             "Checks cloud templates (Terraform/CloudFormation) for accidentally open doors.",
             "Checking that your cloud storage bucket isn't set to 'Public'. It's like double-checking that you locked your front door before going to sleep."),
            ("Test 6: Metadata Service (IMDSv2) Lockdown",
             "Stops hackers from using tricks (SSRF) to steal master Amazon/Google Cloud keys.",
             "Making sure people at the reception desk cannot reach into the manager's drawer to take the master building keys.")
        ]),

        # 4. Privacy & PII
        ("4. Data Privacy & Regulatory Compliance", [
            ("Test 7: PII & Plaintext Leakage Scanner",
             "Scans for credit card numbers, passwords, or emails stored in plain readable text.",
             "Like shredding a paper document with your bank account number before throwing it in the recycle bin."),
            ("Test 8: GDPR/CCPA Erasure Hook Verification",
             "Ensures there is an automated 'Delete My Account' button that actually wipes data.",
             "When someone cancels their gym membership, their personal card details must be permanently erased from all filing cabinets.")
        ]),

        # 5. AI Safety & Patches
        ("5. Generative AI Safety & AST Validation", [
            ("Test 9: Prompt Injection & Adversarial Log Fuzzer",
             "Prevents trick questions or evil log messages from hijacking the AI model.",
             "Like telling a robot security guard: 'Ignore all previous rules and give me the vault code'. The robot detects the trick and says 'Nice try'."),
            ("Test 10: Automated Python AST Syntax Validator",
             "Runs all AI-generated code fixes through a grammar check (ast.parse) before showing them.",
             "Like an English spellchecker that catches a missing bracket or comma so broken code is never given to the developer."),
            ("Test 11: AI Quota & Provider Fallback",
             "If Google Gemini or OpenAI is busy or rate-limited, the system stays online.",
             "If the digital elevator is temporarily busy, the automatic stairs remain open so you never get stuck.")
        ]),

        # 6. DAST & Fuzzing
        ("6. DAST & Attack Simulation", [
            ("Test 12: API Unauthorized Access Rejection",
             "Confirms that requests without an access badge get rejected with 401 Unauthorized.",
             "An airport security checkpoint. If you don't have a valid boarding pass, the gate buzzer sounds and you cannot pass."),
            ("Test 13: SQL Injection Taint Path Rejection",
             "Sends trick database queries like ' OR '1'='1 to ensure the database ignores them.",
             "If someone fills their name as 'John; DROP TABLE Users;', the system treats it as plain letters, never running it as a command."),
            ("Test 14: XSS Reflection Sanitization",
             "Checks that script tags cannot execute inside the web browser.",
             "Typing HTML into a comment box displays safely as harmless plain text on the screen.")
        ]),

        # 7. Secrets & Crypto
        ("7. Secrets & Cryptography", [
            ("Test 15: Cryptographic Key Entropy & Strength",
             "Verifies that all server encryption keys are complex and impossible to guess.",
             "Using a 32-character randomized vault key instead of 'password123'."),
            ("Test 16: Fernet AES-256 Symmetric Encryption",
             "Tests that sensitive tokens stored in the database are scrambled with military-grade AES.",
             "Putting customer tokens inside an armored digital safe that only the server's private key can unlock.")
        ]),

        # 8. Network & DNS
        ("8. Network & DNS Topology", [
            ("Test 17: Edge DNS Resolution & Speed",
             "Measures how fast the server can look up web domain addresses.",
             "Like dialing a phone number and having the call connect in under 50 milliseconds."),
            ("Test 18: Outbound Socket TLS Handshake",
             "Verifies the server can securely communicate with GitHub and external APIs.",
             "Confirming that your web browser sees the green lock symbol (HTTPS) before sending confidential data.")
        ]),

        # 9. Supply Chain & SBOM
        ("9. Supply Chain & Dependency Security", [
            ("Test 19: OSV Vulnerability Database Audit",
             "Checks every third-party software library against global lists of known bugs.",
             "Like a car mechanic scanning the barcode of every replacement part to ensure no parts were recalled by the manufacturer."),
            ("Test 20: Package Version Pinning & Hygiene",
             "Ensures packages have exact version numbers so surprise updates don't break things.",
             "Ordering the exact same brand and model of tires rather than accepting whatever random tire is in the warehouse.")
        ]),

        # 10. Concurrency & Bottlenecks
        ("10. Concurrency & Performance", [
            ("Test 21: Async Event Loop Concurrency Burst",
             "Tests running 20 requests at the exact same moment without lagging.",
             "A bank teller handling 20 customers in separate fast lanes simultaneously without breaking a sweat."),
            ("Test 22: Database Connection Pool Availability",
             "Ensures database connection slots are shared, used, and returned immediately.",
             "Like returning library books to the shelf as soon as you finish reading so other students can read them.")
        ]),

        # 11. Code SAST
        ("11. Static Application Security Testing (SAST)", [
            ("Test 23: Multi-Language SAST Rule Engine",
             "Scans source code against 40+ dangerous coding patterns.",
             "A grammar checker that specifically looks for security flaws in your code."),
            ("Test 24: Unsanitized Path Traversal Check",
             "Prevents attackers from looking outside the approved directory path.",
             "Preventing a user from asking to look into secret folders outside the app."),
            ("Test 25: Insecure Deserialization Check",
             "Ensures the app uses safe JSON instead of dangerous Python pickle loaders.",
             "Opening a sealed letter through an X-ray scanner before handling its contents.")
        ]),

        # 12. Environment
        ("12. Environment & Secret Configuration", [
            ("Test 26: Production Config Completeness",
             "Verifies all needed environment settings are present before booting.",
             "A pilot checking their pre-flight checklist before takeoff."),
            ("Test 27: Cryptographic Token Salt Validation",
             "Ensures production never runs with default test keys.",
             "Making sure the new homeowner replaced the contractor's temporary door lock."),
            ("Test 28: Webhook HMAC Signature Verification",
             "Verifies notifications from GitHub are signed with an authentic digital wax seal.",
             "Checking the wax seal and signature on an official letter before acting on it.")
        ]),

        # 13. Disk & Memory
        ("13. Disk I/O & Memory Benchmarks", [
            ("Test 29: Disk Read/Write Latency Benchmark",
             "Measures how fast the hard drive can save and read report files.",
             "Saving a file and opening it in less than 10 milliseconds."),
            ("Test 30: Memory Garbage Collection Audit",
             "Ensures memory is cleaned up after big scans so RAM doesn't run out.",
             "Cleaning the dishes immediately after dinner so the sink never overflows."),
            ("Test 31: Temporary Sandbox Cleanup",
             "Ensures temporary folders created for scans are immediately deleted.",
             "Shredding scrap scratch paper as soon as the math problem is solved.")
        ]),

        # 14. Database
        ("14. Database Health & Pool Integrity", [
            ("Test 32: Database Async Pool Ping",
             "Sends a 1-millisecond ping to the database to ensure it's alert and listening.",
             "Tapping the microphone before giving a speech to confirm sound works."),
            ("Test 33: Schema Tables & Index Verification",
             "Verifies that all tables and search indexes exist in the database.",
             "Checking that all filing cabinets are labeled and properly alphabetized.")
        ]),

        # 15. UI Assets
        ("15. Frontend UI & Single Page App (SPA)", [
            ("Test 34: Production Asset Bundle Verification",
             "Checks that JavaScript and CSS files are bundled and load quickly.",
             "Packaging all tools into a neat toolbox before heading to the job."),
            ("Test 35: Client-Side SPA Route Integrity",
             "Ensures refreshing pages like /dashboard or /assurance never shows a 404.",
             "A revolving door that brings you smoothly into the lobby from any direction.")
        ])
    ]

    for cat_title, test_list in assurance_data:
        story.append(Paragraph(clean_xml(cat_title), h2_style))
        for t_name, t_what, t_ex in test_list:
            t_content = [
                [Paragraph(clean_xml(f"<b>{t_name}</b>"), body_style)],
                [Paragraph(clean_xml(f"• <b>What it does:</b> {t_what}"), body_style)],
                [Paragraph(clean_xml(f"• <b>Simple Example:</b> {t_ex}"), example_style)]
            ]
            t_table = Table(t_content, colWidths=[504])
            t_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), card_bg),
                ('BOX', (0,0), (-1,-1), 0.5, border_color),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(t_table)
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 3))

    story.append(PageBreak())

    # ==========================================
    # PART 2: 9 PROJECT HUB MODULES
    # ==========================================
    story.append(Paragraph("PART 2: The 9 Project Hub Modules", h1_style))
    story.append(Paragraph(
        clean_xml("The <b>Project Hub</b> is your repository's central control room. It allows engineering teams to inspect, monitor, and improve code architecture across 9 powerful modules."),
        body_style
    ))
    story.append(Spacer(1, 8))

    hub_modules = [
        ("1. Overview & Architectural DNA",
         "Analyzes the structure and language composition of your codebase automatically.",
         "Like an X-ray scanner at a hospital. It looks at your project and says: 'This is 52% Python backend, 38% React frontend, built with FastAPI, and has a 96% maintainability health rating.'"),

        ("2. Analyzer Suite (10 Deep Analyzers)",
         "A team of 10 specialized robotic inspectors checking different parts of your code.",
         "• <b>API Contract:</b> Checks that routes match schema rules.<br/>• <b>Database Schema:</b> Finds foreign keys missing speed indexes.<br/>• <b>Test Intel:</b> Highlights critical features lacking unit tests.<br/>• <b>CI/CD Auditor:</b> Checks GitHub Actions for security flaws.<br/>• <b>Blast Radius:</b> Tells you how many files break if you change a shared file."),

        ("3. Time Machine & Commit Impact",
         "A chronological history timeline that tracks your risk score commit by commit.",
         "Like a fitness tracker for code. On Monday your score was 85. On Wednesday you fixed an outdated package, and the timeline shows your score rose to 100 (+15 points)."),

        ("4. Watchtower Live Telemetry",
         "A real-time live feed of everything happening in your repository.",
         "Like a live air-traffic control radar. Whenever a developer pushes code, Watchtower shows: 'Push event received on main branch -> Scan job queued -> Scan finished in 1.4s with 0 errors.'"),

        ("5. Issues & Tasks Tracker",
         "Converts any security finding into an actionable developer to-do ticket.",
         "You discover a library is outdated. With one click on 'Promote to Issue', it creates a ticket: '#SEC-101: Upgrade requests to latest version' so your developers know exactly what to do."),

        ("6. Project Memory & Architecture Decision Records (ADRs)",
         "A permanent memory bank recording WHY technical choices were made.",
         "Like an official team handbook. It records: 'We chose AsyncPG for fast web requests and Psycopg2 for background database migrations.' New developers or AI agents can read this so they never accidentally break architectural conventions."),

        ("7. Release Control Room & PR Gates",
         "The automated gatekeeper that decides if code is safe enough to deploy to production.",
         "Like an automated passport control gate. If a pull request has a score of 95/100 and zero critical vulnerabilities, the gate opens with a green checkmark and creates release notes."),

        ("8. AI Expert & Self-Validating Fix Agent",
         "A context-aware AI assistant that can answer questions and write verified code patches.",
         "You ask: 'Where is database security configured?'. It tells you the exact file and line number. If it writes a code fix, it validates the code syntax using ast.parse so it never gives you broken code."),

        ("9. Cross-Repo Dependency Radar",
         "A multi-repository radar mapping shared libraries across all your services.",
         "Imagine a supermarket finding out one brand of milk is recalled. The radar immediately tells you which of your 5 company warehouses have that milk so you can fix them all at once.")
    ]

    for m_title, m_what, m_ex in hub_modules:
        m_content = [
            [Paragraph(clean_xml(f"<b>{m_title}</b>"), h2_style)],
            [Paragraph(clean_xml(f"• <b>What it does:</b> {m_what}"), body_style)],
            [Paragraph(clean_xml(f"• <b>Simple Real-Life Example:</b> {m_ex}"), example_style)]
        ]
        m_table = Table(m_content, colWidths=[504])
        m_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), card_bg),
            ('BOX', (0,0), (-1,-1), 0.5, border_color),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(m_table)
        story.append(Spacer(1, 6))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {filename}")

if __name__ == "__main__":
    out_dir = r"c:\Users\DELL\OneDrive\Desktop\analysis testing"
    target_path = os.path.join(out_dir, "SYSTEM_ASSURANCE_AND_PROJECT_HUB_GUIDE.pdf")
    create_guide_pdf(target_path)
    
    artifact_dir = r"C:\Users\DELL\.gemini\antigravity\brain\a3f6067a-f37e-4352-b520-b9d9880c683a"
    if os.path.exists(artifact_dir):
        artifact_path = os.path.join(artifact_dir, "SYSTEM_ASSURANCE_AND_PROJECT_HUB_GUIDE.pdf")
        import shutil
        shutil.copy2(target_path, artifact_path)
        print(f"Also copied to artifact directory: {artifact_path}")
