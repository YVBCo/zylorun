import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const distDir = path.resolve(__dirname, '../dist');
const indexHtmlPath = path.join(distDir, 'index.html');

console.log('--- Verifying Frontend Production Build Assets ---');

if (!fs.existsSync(indexHtmlPath)) {
  console.error('FAIL: dist/index.html does not exist! Run npm run build first.');
  process.exit(1);
}

const htmlContent = fs.readFileSync(indexHtmlPath, 'utf8');

// 1. Extract all script and link tags from index.html
const assetRegex = /(?:src|href)="(\/assets\/[^"]+)"/g;
const referencedAssets = [];
let match;
while ((match = assetRegex.exec(htmlContent)) !== null) {
  referencedAssets.push(match[1]);
}

console.log(`Found ${referencedAssets.length} referenced assets in index.html:`, referencedAssets);

if (referencedAssets.length === 0) {
  console.error('FAIL: No assets found in index.html!');
  process.exit(1);
}

// 2. Verify all referenced files exist on disk
for (const assetPath of referencedAssets) {
  const filePath = path.join(distDir, assetPath.replace(/^\//, ''));
  if (!fs.existsSync(filePath)) {
    console.error(`FAIL: Referenced asset does not exist on disk: ${filePath}`);
    process.exit(1);
  }
  const stat = fs.statSync(filePath);
  if (stat.size === 0) {
    console.error(`FAIL: Asset is 0 bytes: ${filePath}`);
    process.exit(1);
  }
  console.log(`✓ Verified asset on disk: ${assetPath} (${stat.size} bytes)`);
}

// 3. Test static server preview and verify content-types and deep link routing
const mimeTypes = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.jpg': 'image/jpeg',
  '.png': 'image/png',
  '.svg': 'image/svg+xml'
};

const server = http.createServer((req, res) => {
  const urlPath = req.url.split('?')[0];

  // Emulate Vercel asset handling: missing assets return 404
  if (urlPath.startsWith('/assets/')) {
    const assetFile = path.join(distDir, urlPath.replace(/^\//, ''));
    if (fs.existsSync(assetFile)) {
      const ext = path.extname(assetFile);
      res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
      fs.createReadStream(assetFile).pipe(res);
      return;
    } else {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Asset Not Found');
      return;
    }
  }

  // Emulate Vercel SPA rewrite: any route returns index.html
  res.writeHead(200, { 'Content-Type': 'text/html' });
  fs.createReadStream(indexHtmlPath).pipe(res);
});

const PORT = 4173;
server.listen(PORT, async () => {
  console.log(`Static preview server listening on port ${PORT}`);

  try {
    // Test 1: Fetch index.html
    const indexRes = await fetch(`http://localhost:${PORT}/`);
    if (indexRes.status !== 200) throw new Error(`/ returned status ${indexRes.status}`);
    const indexHtml = await indexRes.text();
    if (!indexHtml.includes('<div id="root">')) throw new Error('index.html missing root element');
    console.log('✓ Route / returns valid HTML (200 OK)');

    // Test 2: Fetch every asset referenced in index.html
    for (const assetPath of referencedAssets) {
      const res = await fetch(`http://localhost:${PORT}${assetPath}`);
      if (res.status !== 200) throw new Error(`${assetPath} returned status ${res.status}`);
      const contentType = res.headers.get('content-type') || '';
      if (assetPath.endsWith('.js') && !contentType.includes('javascript')) {
        throw new Error(`${assetPath} served with wrong MIME type: ${contentType}`);
      }
      if (assetPath.endsWith('.css') && !contentType.includes('css')) {
        throw new Error(`${assetPath} served with wrong MIME type: ${contentType}`);
      }
      console.log(`✓ Asset ${assetPath} returned 200 OK with correct MIME (${contentType})`);
    }

    // Test 3: Deep link navigation (e.g. /repositories/8/scans/76/audit)
    const deepRoutes = [
      '/dashboard',
      '/onboarding',
      '/passport',
      '/repositories/8/scans/76/audit'
    ];
    for (const route of deepRoutes) {
      const deepRes = await fetch(`http://localhost:${PORT}${route}`);
      if (deepRes.status !== 200) throw new Error(`${route} returned status ${deepRes.status}`);
      const deepHtml = await deepRes.text();
      if (!deepHtml.includes('<div id="root">')) throw new Error(`${route} did not serve SPA index.html`);
      console.log(`✓ Deep route ${route} rewrites cleanly to index.html (200 OK)`);
    }

    // Test 4: Missing asset returns 404 and does NOT return text/html
    const missingRes = await fetch(`http://localhost:${PORT}/assets/nonexistent-chunk-12345.js`);
    if (missingRes.status !== 404) {
      throw new Error(`Missing asset returned status ${missingRes.status} instead of 404!`);
    }
    const missingContentType = missingRes.headers.get('content-type') || '';
    if (missingContentType.includes('text/html')) {
      throw new Error(`Missing asset served text/html!`);
    }
    console.log('✓ Missing asset returns 404 without serving text/html');

    console.log('\n--- ALL BUILD ASSET CHECKS PASSED (100% SUCCESS) ---');
  } catch (err) {
    console.error('FAIL in asset verification:', err);
    process.exitCode = 1;
  } finally {
    server.close();
  }
});
