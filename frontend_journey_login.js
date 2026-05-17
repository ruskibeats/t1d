const { chromium } = require('playwright');

(async () => {
  const FRONTEND_URL = 'http://192.168.0.92:3002';
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  console.log('Browser launched.');

  async function captureAndLog(name) {
    const path = `/root/t1d/journey_${name}.png`;
    await page.screenshot({ path, fullPage: true });
    console.log(`Captured ${name} to ${path}`);
  }

  // 1. Login Page
  await page.goto(`${FRONTEND_URL}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  console.log('Navigated to login page.');
  await captureAndLog('login_page');

  await page.fill('input[type="email"]', 'demo@example.com');
  await page.fill('input[type="password"]', 'demopass123');
  
  // Ensure the submit button exists and is enabled before clicking
  await page.waitForSelector('button[type="submit"]', { state: 'visible', timeout: 5000 });
  await Promise.all([
    page.waitForURL(`${FRONTEND_URL}/dashboard`, { waitUntil: 'networkidle', timeout: 30000 }),
    page.click('button[type="submit"]')
  ]);
  console.log('Logged in and navigated to dashboard.');
  await captureAndLog('dashboard_after_login');

  await browser.close();
  console.log('Browser closed.');

})().catch(e => { console.error("FAIL:", e.message); process.exit(1) });
