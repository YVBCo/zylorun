const WebSocket = require('ws'); // Might need to install ws

async function runTest() {
  const url = 'https://software-testing-teq9.onrender.com';
  
  // 1. Get Token (admin / secret is the default bootstrap)
  let res = await fetch(`${url}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'username=admin&password=secret'
  });
  if (!res.ok) {
    console.log('Login failed', await res.text());
    return;
  }
  let tokenData = await res.json();
  const token = tokenData.access_token;
  console.log('Got token:', token);
  
  // 2. Add Command (ping)
  res = await fetch(`${url}/commands/`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: "PingTest", executable: "ping", allowed_args: "[]", regex_rules: "[]" })
  });
  const cmd = await res.json();
  console.log('Created command:', cmd);
  
  // 3. Add Target
  res = await fetch(`${url}/targets/`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: "Localhost", host: "127.0.0.1" })
  });
  const target = await res.json();
  console.log('Created target:', target);

  // 4. Test WebSocket
  const wsUrl = `wss://software-testing-teq9.onrender.com/runs/ws/${cmd.id}/${target.id}?token=${token}`;
  console.log('Connecting to WS:', wsUrl);
  
  const ws = new WebSocket(wsUrl);
  
  ws.on('open', () => {
    console.log('WS OPENED');
    ws.send(JSON.stringify({ args: [] }));
  });
  
  ws.on('message', (data) => {
    console.log('WS MSG:', data.toString());
  });
  
  ws.on('close', (code, reason) => {
    console.log('WS CLOSED:', code, reason.toString());
    process.exit(0);
  });
  
  ws.on('error', (err) => {
    console.log('WS ERROR:', err);
    process.exit(1);
  });
}

runTest().catch(console.error);
