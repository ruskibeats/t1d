
const { chromium } = require('playwright');

(async () => {
  const URL = 'http://192.168.0.92:3002';
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  
  await page.goto(URL + '/login');
  await page.fill('input[type="email"]', 'demo@example.com');
  await page.fill('input[type="password"]', 'demopass123');
  await page.click('button[type="submit"]');
  await new Promise(r => setTimeout(r, 5000));
  await page.screenshot({ path: '/root/t1d/journey_dash.png' });
  console.log('Dashboard screenshot');

  await page.goto(URL + '/chat');
  await new Promise(r => setTimeout(r, 3000));
  await page.screenshot({ path: '/root/t1d/journey_chat.png' });
  console.log('Chat screenshot');
  
  await page.goto(URL + '/patterns');
  await new Promise(r => setTimeout(r, 3000));
  await page.screenshot({ path: '/root/t1d/journey_patterns.png' });
  console.log('Patterns screenshot');

  await page.goto(URL + '/settings');
  await new Promise(r => setTimeout(r, 3000));
  await page.screenshot({ path: '/root/t1d/journey_settings.png' });
  console.log('Settings screenshot');

  await browser.close();
  console.log('All done');
})().catch(e => { console.error(e.message); process.exit(1); });
