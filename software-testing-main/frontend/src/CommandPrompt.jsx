import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Terminal, Trash2 } from 'lucide-react';

const defaultTests = [
  {
    id: 1,
    name: 'Vulnerable Third-Party Libraries (SCA)',
    commands: [
      { id: 11, commandStr: 'cd edoc-next' },
      { id: 12, commandStr: 'npm audit --no-workspaces' }
    ]
  },
  {
    id: 2,
    name: 'Hardcoded Secrets, Passwords, and Tokens',
    commands: [
      { id: 21, commandStr: 'findstr /S /I /N "password" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' },
      { id: 22, commandStr: 'findstr /S /I /N "token" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' },
      { id: 23, commandStr: 'findstr /S /I /N "secret" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' }
    ]
  },
  {
    id: 3,
    name: 'Environment Variable Leakage',
    commands: [
      { id: 31, commandStr: 'dir .env*' }
    ]
  },
  {
    id: 4,
    name: 'Dangerous Functions (XSS & RCE Risks)',
    commands: [
      { id: 41, commandStr: 'findstr /S /I /N "dangerouslySetInnerHTML" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' },
      { id: 42, commandStr: 'findstr /S /I /N "eval(" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' }
    ]
  },
  {
    id: 5,
    name: 'Developer Leftovers (Information Disclosure)',
    commands: [
      { id: 51, commandStr: 'findstr /S /I /N "TODO" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' },
      { id: 52, commandStr: 'findstr /S /I /N "FIXME" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' },
      { id: 53, commandStr: 'findstr /S /I /N "localhost" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' },
      { id: 54, commandStr: 'findstr /S /I /N "bypass" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' }
    ]
  },
  {
    id: 6,
    name: 'Missing Security Headers',
    commands: [
      { id: 61, commandStr: 'type next.config.js' }
    ]
  },
  {
    id: 7,
    name: 'SQL Injection Hotspots (Prisma)',
    commands: [
      { id: 71, commandStr: 'findstr /S /I /N "$queryRawUnsafe" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' },
      { id: 72, commandStr: 'findstr /S /I /N "$executeRawUnsafe" *.js *.ts *.jsx *.tsx | findstr /V "node_modules" | findstr /V ".next"' }
    ]
  },
  {
    id: 8,
    name: 'SAST (Static Application Security Testing)',
    commands: [
      { id: 81, commandStr: 'cd edoc-next' },
      { id: 82, commandStr: 'npx eslint . --ext .js,.jsx,.ts,.tsx' }
    ]
  },
  {
    id: 9,
    name: 'DAST (Dynamic Application Security Testing)',
    commands: [
      { id: 91, commandStr: 'cd edoc-next' },
      { id: 92, commandStr: 'npm run dev' }
    ]
  },
  {
    id: 10,
    name: 'Check response headers',
    commands: [
      { id: 101, commandStr: 'curl -I https://yourwebsite.com' }
    ]
  },
  {
    id: 11,
    name: 'Check the SSL/TLS certificate',
    commands: [
      { id: 111, commandStr: 'openssl s_client -connect yourwebsite.com:443 -servername yourwebsite.com' }
    ]
  },
  {
    id: 12,
    name: 'Fix missing headers (Vercel hosting)',
    commands: [
      { id: 121, commandStr: 'git add vercel.json' },
      { id: 122, commandStr: 'git commit -m "add security headers"' },
      { id: 123, commandStr: 'git push' }
    ]
  },
  {
    id: 13,
    name: 'Linux environment for deeper scanning',
    commands: [
      { id: 131, commandStr: 'wsl --install -d kali-linux' },
      { id: 132, commandStr: 'sudo apt update && sudo apt install nikto -y' }
    ]
  },
  {
    id: 14,
    name: 'Basic vulnerability / misconfiguration scan',
    commands: [
      { id: 141, commandStr: 'nikto -h https://yourwebsite.com' }
    ]
  },
  {
    id: 15,
    name: 'HTTP 4xx Client Errors (Pages 10-11)',
    commands: [
      { id: 1501, commandStr: '400 Bad Request: Malformed URL, broken JSON' },
      { id: 1502, commandStr: '401 Unauthorized: Login missing or invalid' },
      { id: 1503, commandStr: '403 Forbidden: Server knows you but refuses access' },
      { id: 1504, commandStr: '404 Not Found: Page or resource does not exist' },
      { id: 1505, commandStr: '429 Too Many Requests: Rate limiting against brute force' }
    ]
  },
  {
    id: 16,
    name: 'HTTP 5xx Server Errors (Page 12)',
    commands: [
      { id: 1601, commandStr: '500 Internal Server Error: Code bug, crashed script' },
      { id: 1602, commandStr: '502 Bad Gateway: Proxy got invalid reply from upstream' },
      { id: 1603, commandStr: '503 Service Unavailable: Maintenance or overload' },
      { id: 1604, commandStr: '504 Gateway Timeout: Slow database or API' },
      { id: 1605, commandStr: '520-530: Cloudflare specific origin errors' }
    ]
  },
  {
    id: 17,
    name: 'HTTP Security Action Plan (Page 13)',
    commands: [
      { id: 1701, commandStr: '401/403: Many 401s from one IP can mean password guessing' },
      { id: 1702, commandStr: '404: Watch logs; do not reveal extra detail' },
      { id: 1703, commandStr: '429: Keep enabled on login and forms' },
      { id: 1704, commandStr: '400/414/431: Validate input and set header size limits' },
      { id: 1705, commandStr: '413/415: Limit file size and allowed types' },
      { id: 1706, commandStr: '426/497: Redirect to HTTPS and enable HSTS' },
      { id: 1707, commandStr: '500: Show generic error page; log details privately' },
      { id: 1708, commandStr: '502/503/504: Check traffic, use CDN or WAF, add capacity' },
      { id: 1709, commandStr: '525/526: Renew or fix the origin SSL certificate' }
    ]
  }
];

export default function CommandPrompt({ token }) {
  const [tests, setTests] = useState(defaultTests);
  const [newTestName, setNewTestName] = useState('');

  const addTest = () => {
    if (newTestName.trim()) {
      setTests([...tests, { id: Date.now(), name: newTestName, commands: [] }]);
      setNewTestName('');
    }
  };

  const removeTest = (testId) => {
    setTests(tests.filter(t => t.id !== testId));
  };

  const addCommandToTest = (testId) => {
    setTests(tests.map(test => {
      if (test.id === testId) {
        if (test.commands.length >= 20) {
          alert("You can add up to 20 commands per test.");
          return test;
        }
        return { ...test, commands: [...test.commands, { id: Date.now(), commandStr: '' }] };
      }
      return test;
    }));
  };

  const updateCommand = (testId, cmdId, val) => {
    setTests(tests.map(test => {
      if (test.id === testId) {
        return {
          ...test,
          commands: test.commands.map(c => c.id === cmdId ? { ...c, commandStr: val } : c)
        };
      }
      return test;
    }));
  };

  const removeCommand = (testId, cmdId) => {
    setTests(tests.map(test => {
      if (test.id === testId) {
        return { ...test, commands: test.commands.filter(c => c.id !== cmdId) };
      }
      return test;
    }));
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 md:p-8 h-full flex flex-col">
      <h1 className="text-2xl md:text-3xl font-bold text-white tracking-wide mb-8 flex items-center gap-3">
        <Terminal className="text-cyan-accent w-8 h-8" /> Command Prompt
      </h1>

      <div className="bg-black/40 border border-gray-800 p-6 rounded-xl shadow-lg mb-8">
        <h2 className="text-xl text-white font-semibold mb-4">Add Security Test</h2>
        <div className="flex gap-4">
          <input 
            type="text" 
            placeholder="Enter Test Name (e.g., Network Recon)"
            className="flex-1 bg-black/50 border border-gray-800 text-white p-3 rounded font-mono outline-none focus:border-cyan-accent transition"
            value={newTestName}
            onChange={(e) => setNewTestName(e.target.value)}
          />
          <button 
            onClick={addTest}
            className="bg-cyan-accent text-black px-6 py-3 rounded font-bold hover:bg-cyan-400 transition flex items-center gap-2"
          >
            <Plus className="w-5 h-5" /> Add Test
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-6 pb-10">
        {tests.length === 0 ? (
          <div className="text-gray-500 text-center italic mt-10">No security tests added yet.</div>
        ) : (
          tests.map(test => (
            <div key={test.id} className="bg-navy-panel border border-cyan-accent/20 p-5 rounded-lg shadow-md relative">
              <button 
                onClick={() => removeTest(test.id)} 
                className="absolute top-4 right-4 text-gray-600 hover:text-red-500 transition"
              >
                <Trash2 className="w-5 h-5" />
              </button>
              <div className="flex justify-between items-center mb-4 border-b border-gray-800 pb-3 pr-10">
                <h3 className="text-lg font-bold text-cyan-accent">{test.name}</h3>
                <span className="text-xs text-gray-400 font-mono">{test.commands.length} / 20 Commands</span>
              </div>
              
              <div className="space-y-3 mb-4">
                {test.commands.map((cmd, index) => (
                  <div key={cmd.id} className="flex gap-3 items-center">
                    <span className="text-gray-500 font-mono text-sm w-6 text-right">{index + 1}.</span>
                    <input 
                      type="text"
                      placeholder="Enter command (e.g., nmap -sV target)"
                      className="flex-1 bg-black/30 border border-gray-700 text-gray-200 p-2 rounded font-mono text-sm outline-none focus:border-cyan-accent"
                      value={cmd.commandStr}
                      onChange={(e) => updateCommand(test.id, cmd.id, e.target.value)}
                    />
                    <button onClick={() => removeCommand(test.id, cmd.id)} className="text-red-500 hover:text-red-400 p-2 transition">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>

              {test.commands.length < 20 && (
                <button 
                  onClick={() => addCommandToTest(test.id)}
                  className="text-sm flex items-center gap-1 text-gray-400 hover:text-cyan-accent transition ml-9"
                >
                  <Plus className="w-4 h-4" /> Add Command
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </motion.div>
  );
}
