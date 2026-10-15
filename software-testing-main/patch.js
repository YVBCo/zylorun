const fs = require('fs');
let code = fs.readFileSync('frontend/src/Login.jsx', 'utf8');

// 1. Add pendingLogin state
code = code.replace(
  'const [lockoutTimer, setLockoutTimer] = useState(0);',
  'const [lockoutTimer, setLockoutTimer] = useState(0);\n  const [pendingLogin, setPendingLogin] = useState(false);'
);

// 2. Fix intro effect
code = code.replace(
  /const t1 = setTimeout\(\(\) => setIntroStep\(1\), 1800\);\n\s*const t2 = setTimeout\(\(\) => setIntroStep\(2\), 3500\);/,
  `if (sessionStorage.getItem('introPlayed')) {
      setIntroStep(2);
    } else {
      const t1 = setTimeout(() => { setIntroStep(1); sessionStorage.setItem('introPlayed', 'true'); }, 1500);
      const t2 = setTimeout(() => setIntroStep(2), 2500);
      return () => { clearTimeout(t1); clearTimeout(t2); };
    }`
);

// Remove the old clearTimeout logic
code = code.replace(
  /return \(\) => \{\n\s*clearTimeout\(t1\); clearTimeout\(t2\);\n\s*window.removeEventListener\('keydown', handleKey\);\n\s*\};/,
  `return () => {
      window.removeEventListener('keydown', handleKey);
    };`
);

// 3. pendingLogin useEffect
code = code.replace(
  /useEffect\(\(\) => \{\n\s*if \(lockoutTimer > 0\)/,
  `useEffect(() => {
    if (pendingLogin && backendState === 'connected') {
      setPendingLogin(false);
      handleLogin(new Event('submit'));
    }
  }, [backendState, pendingLogin]);

  useEffect(() => {
    if (lockoutTimer > 0)`
);

// 4. Update handleLogin for connecting state
code = code.replace(
  /const handleLogin = async \(e\) => \{\n\s*e.preventDefault\(\);\n\s*if \(lockoutTimer > 0\) return;\n\s*setLoading\(true\);\n\s*setErrorMsg\(''\);/,
  `const handleLogin = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (lockoutTimer > 0) return;
    
    if (backendState === 'connecting') {
      setErrorMsg('Backend is still waking up, please wait...');
      setPendingLogin(true);
      return;
    }

    setLoading(true);
    setErrorMsg('');`
);

// 5. Update Boot Text component to support click/skip and show WAKING UP in amber
code = code.replace(
  /if \(introStep === 0 && !prefersReducedMotion && effectsOn\) \{\n\s*return \([\s\S]*?;\n\s*\}/,
  `const skipIntro = () => { setIntroStep(2); sessionStorage.setItem('introPlayed', 'true'); };
  
  // Skip on any key press
  useEffect(() => {
    if (introStep === 0) {
      const skip = () => skipIntro();
      window.addEventListener('keydown', skip);
      return () => window.removeEventListener('keydown', skip);
    }
  }, [introStep]);

  if (introStep === 0 && !prefersReducedMotion && effectsOn) {
    return (
      <div 
        className="min-h-screen bg-[#0b1220] flex items-center justify-center font-mono text-cyan-500 text-sm md:text-lg cursor-pointer"
        onClick={skipIntro}
      >
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2 relative">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>{\`> INITIALIZING SECURE CHANNEL...\`}</motion.div>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }}>{\`> LOADING ENCRYPTION MODULES... OK\`}</motion.div>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.4 }}>
            {\`> VERIFYING BACKEND... \`} 
            <span className={backendState === 'connected' ? 'text-green-500' : 'text-amber-500'}>
              {backendState === 'connected' ? 'OK' : 'WAKING UP'}
            </span>
          </motion.div>
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 0.5 }} transition={{ delay: 1.8 }}
            className="absolute -bottom-10 left-0 text-xs text-gray-500"
          >
            [Press any key or click to skip]
          </motion.div>
        </motion.div>
      </div>
    );
  }`
);

fs.writeFileSync('frontend/src/Login.jsx', code);
console.log('Fixed Login.jsx');
