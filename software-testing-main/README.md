# 🛡️ SecRunner: Enterprise Security Automation Platform

SecRunner is a full-stack security orchestration tool designed to automate, track, and analyze command-line security scans across multiple target IPs. It features a powerful FastAPI backend and a sleek React/Vite frontend.

## ✨ Core Features
- **Live Terminal Execution:** Run any configured OS command directly from the browser, with real-time stdout streaming via WebSockets.
- **Dynamic Command & Target Management:** Add new Security Tools and Target IP Addresses directly from the Settings UI—no code changes required.
- **Ultra-Fast Log Analysis (New!):** Instantly analyze logs locally to detect critical security vulnerabilities in 0.001 seconds.
- **Massive ZIP Extraction in Browser (New!):** Upload massive .zip files containing raw security logs. SecRunner automatically filters out binary files and folders (like 
ode_modules) and instantly extracts the text logs for analysis—all securely within your browser!
- **Advanced AI Prompt Generator (New!):** Choose between "Standard Quick Fix" and "Senior Engineer (Advanced)" prompts to generate massive, high-quality, 7-step prompt templates to send to Gemini or ChatGPT to fix your errors.
- **PDF Exporting:** Cleanly export your security findings into professional PDF reports using jspdf.

## 💻 Tech Stack
- **Backend:** Python, FastAPI, SQLite, SQLAlchemy, WebSockets
- **Frontend:** React, Vite, Tailwind CSS, JSZip, jsPDF
- **AI Integration:** Google Gemini Flash API (gemini-flash-latest)
- **Hosting:** Vercel (Frontend) & Render (Backend)

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
`ash
git clone https://github.com/bnyashavanth-prog/software-testing.git
cd software-testing/sec-runner
`

### 2. Backend Setup (FastAPI)
`ash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
`
**Important:** Create a .env file inside the ackend folder and add your Gemini API Key:
`env
GEMINI_API_KEY=your_api_key_here
`
Run the server:
`ash
uvicorn app.main:app --reload
`
*Note: Make sure to hit the /runs/bootstrap endpoint on first launch to create the default admin user!*

### 3. Frontend Setup (React)
Open a new terminal window:
`ash
cd frontend
npm install
npm run dev
`
Visit http://localhost:5173 in your browser. The default login is dmin / secret.

---

## 🌍 Live Deployment
SecRunner is configured for instant deployment!
- The Frontend is automatically configured for **Vercel** (with proper SPA fallback routing in ercel.json).
- The Backend is fully configured for **Render**. To prevent cold starts, the frontend features an automatic background warmup ping!

