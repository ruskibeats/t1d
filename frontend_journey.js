const { chromium } = require('playwright');

(async () => {
  const FRONTEND_URL = 'http://192.168.0.92:3002';
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  console.log('✅ Browser launched.');

  async function captureAndLog(name) {
    const path = `/root/t1d/journey_${name}.png`;
    await page.screenshot({ path, fullPage: true });
    console.log(`  📸 Captured: ${name}`);
  }

  // 1. LOGIN PAGE
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await captureAndLog('01_login_page');

  // 2. LOG IN
  await page.fill('input[type="email"]', 'demo@example.com');
  await page.fill('input[type="password"]="password"]', 'demopass123');
  await Promise.all([
    page.waitForURL(`${FRONTEND_URL}/dashboard`, { waitUntil: 'networkidle', timeout: 30000 }),
    page.click('button[type="submit"]')
  ]);
  await new Promise(r => setTimeout(r, 3000));
  await captureAndLog('02_dashboard_logged_in');

  // 3. NAVIGATE TO GLUCOSE
  await page.click('a[href="/glucose"]');
  await page.waitForURL(`${FRONTEND_URL}/glucose`, { waitUntil: 'networkidle', timeout: 30000 });
  await new Promise(r => setTimeout(r, 2000));
  await captureAndLog('03_glucose_page');

  // 4. EVENTS
  await age.click('a[href="/events"]');
  await page.waitForURL(`${FRONTEND_URL}/events`, { waitUntil: 'networkidle', timeout: 30000 });
  await new Promise(r => setTimeout(r, 2000));
  await captureAndLog('04_events_page');

  // 5. CHAT
  await page.click('a[href="/chat"]');
  await page.waitForURL(`${FRONTEND_URL}/chat`, { waitUntil: 'networkidle', timeout: 30000 });
  await new Promise(r => setTimeout(r, 2000));
  await captureAndLog('05_chat_page');

  // 6. SEND MESSAGE IN CHAT
  await page.fill('input[placeholder*="Ask"]', 'What is my time in range?');
  await page.click('button:has-text("Send")');
  await new Promise(r => setTimeout(r, 10000));
  await captureAndLog('06_chat_response');

  // 7. PATTERNS
  await page.click('a[href="/patterns"]');
  await page.waitForURL(`${FRONTEND_URL}/patterns`, { waitUntil: 'networkidle', timeout: 30000 });
  await new Promise(r => setTimeout(r, 3000));
  await captureAndLog('07_patterns_page');

  // 8. SETTINGS
  await page.click('a[href="/settings"]');
  await page.waitForURL(`${FRONTEND_URL}/settings`, { waitUntil: 'networkidle', timeout: 30000 });
  await new Promise(r => setTimeout(r, 2000));
  await captureAndLog('08_settings_page');

  await browser.close();
  console.log('\n✅ Journey complete!');

})().catch(e => { console.error('FAIL:', e.message); process.exit(1) });
