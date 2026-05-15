import { chromium } from 'playwright'
import { mkdir, rename } from 'node:fs/promises'
import path from 'node:path'

const baseUrl = process.env.T1D_FRONTEND_URL ?? 'http://localhost:3000'
const outDir = path.resolve('promo')
const videoDir = path.join(outDir, 'raw')

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function setCaption(page, title, body = '') {
  await page.evaluate(({ title, body }) => {
    const caption = document.querySelector('[data-promo-caption]')
    if (!caption) return
    caption.querySelector('[data-title]').textContent = title
    caption.querySelector('[data-body]').textContent = body
    caption.animate(
      [
        { transform: 'translateY(10px)', opacity: 0.72 },
        { transform: 'translateY(0)', opacity: 1 },
      ],
      { duration: 420, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }
    )
  }, { title, body })
}

async function injectPromoChrome(page) {
  await page.addStyleTag({
    content: `
      [data-promo-caption] {
        position: fixed;
        left: 34px;
        bottom: 30px;
        z-index: 999999;
        width: min(560px, calc(100vw - 68px));
        padding: 18px 20px;
        border-radius: 24px;
        border: 1px solid oklch(1 0 0 / 0.16);
        background: linear-gradient(135deg, oklch(0.19 0.045 255 / 0.88), oklch(0.26 0.07 255 / 0.82));
        box-shadow: 0 28px 90px oklch(0.18 0.05 255 / 0.38);
        color: oklch(0.97 0.01 245);
        backdrop-filter: blur(18px);
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }
      [data-promo-caption]::before {
        content: "";
        display: inline-block;
        width: 9px;
        height: 9px;
        margin-right: 8px;
        border-radius: 999px;
        background: oklch(0.74 0.14 178);
        box-shadow: 0 0 0 7px oklch(0.74 0.14 178 / 0.16);
        vertical-align: 2px;
      }
      [data-promo-caption] [data-title] {
        display: inline;
        font-size: 18px;
        line-height: 1.1;
        font-weight: 900;
        letter-spacing: -0.03em;
      }
      [data-promo-caption] [data-body] {
        display: block;
        margin-top: 8px;
        color: oklch(0.84 0.025 245);
        font-size: 14px;
        line-height: 1.45;
        font-weight: 650;
      }
      [data-promo-watermark] {
        position: fixed;
        right: 34px;
        top: 26px;
        z-index: 999999;
        display: inline-flex;
        align-items: center;
        gap: 9px;
        border: 1px solid oklch(0.88 0.02 250);
        border-radius: 999px;
        padding: 10px 14px;
        background: oklch(0.98 0.01 245 / 0.82);
        box-shadow: 0 14px 40px oklch(0.25 0.05 255 / 0.12);
        color: oklch(0.22 0.04 255);
        font: 850 13px/1 Inter, ui-sans-serif, system-ui;
        backdrop-filter: blur(14px);
      }
      [data-promo-watermark] span {
        width: 9px;
        height: 9px;
        border-radius: 999px;
        background: oklch(0.7 0.14 178);
      }
    `,
  })
  await page.evaluate(() => {
    document.querySelector('[data-promo-caption]')?.remove()
    document.querySelector('[data-promo-watermark]')?.remove()

    const caption = document.createElement('div')
    caption.setAttribute('data-promo-caption', '')
    caption.innerHTML = '<span data-title></span><span data-body></span>'
    document.body.appendChild(caption)

    const watermark = document.createElement('div')
    watermark.setAttribute('data-promo-watermark', '')
    watermark.innerHTML = '<span></span> T1D Companion'
    document.body.appendChild(watermark)
  })
}

async function clickText(page, text) {
  await page.getByText(text, { exact: false }).first().click()
}

await mkdir(videoDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
  recordVideo: {
    dir: videoDir,
    size: { width: 1440, height: 900 },
  },
})

const page = await context.newPage()
page.setDefaultTimeout(12_000)

await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle' })
await injectPromoChrome(page)
await setCaption(page, 'A personal pattern layer for Type 1 diabetes', 'Sensor data, meals, movement, sleep, stress, and safe conversational insight in one place.')
await wait(1400)

await page.getByRole('button', { name: /try demo workspace/i }).click()
await page.waitForURL(/dashboard/, { timeout: 8000 }).catch(() => {})
await page.waitForLoadState('networkidle').catch(() => {})
await injectPromoChrome(page)
await setCaption(page, 'Live cockpit, instantly populated', 'The dashboard explains the current signal, time in range, and recent context without feeling clinical or generic.')
await wait(1800)

await page.mouse.move(830, 620, { steps: 28 })
await wait(600)
await page.mouse.move(520, 450, { steps: 20 })
await wait(500)
await clickText(page, '7D')
await wait(900)
await setCaption(page, 'Glucose trace with target context', 'Charting shows the rhythm, target band, excursions, and sensor cadence at a glance.')
await page.mouse.move(610, 715, { steps: 30 })
await wait(1600)

await page.getByRole('link', { name: /glucose/i }).click()
await page.waitForLoadState('networkidle').catch(() => {})
await injectPromoChrome(page)
await setCaption(page, 'Raw readings stay inspectable', 'Users can review individual entries, sources, status, and trend deltas when they need detail.')
await wait(1700)
await page.mouse.wheel(0, 520)
await wait(1000)

await page.getByRole('link', { name: /patterns/i }).click()
await page.waitForLoadState('networkidle').catch(() => {})
await injectPromoChrome(page)
await setCaption(page, 'Patterns, not one-off numbers', 'The app looks for repeatable context around food, exercise, and overnight windows.')
await wait(1900)
await page.mouse.wheel(0, 420)
await wait(1200)

await page.getByRole('link', { name: /ai chat/i }).click()
await page.waitForLoadState('networkidle').catch(() => {})
await injectPromoChrome(page)
await setCaption(page, 'Ask the pattern layer', 'The assistant explains what the data suggests, while staying inside safety boundaries.')
await wait(1200)
const input = page.getByPlaceholder(/Ask about patterns/i)
await input.click()
await input.fill('Why do I rise later after pizza?')
await wait(450)
await page.getByRole('button', { name: /send/i }).click()
await wait(2600)

await setCaption(page, 'Educational only, safety first', 'No autonomous dosing, no treatment changes, and clear escalation when urgent language appears.')
await wait(1800)

await page.getByRole('link', { name: /settings/i }).click()
await page.waitForLoadState('networkidle').catch(() => {})
await injectPromoChrome(page)
await setCaption(page, 'Ready for sensors and beta testing', 'Dexcom, Nightscout, manual entry, notifications, and guardrails are designed as one product surface.')
await wait(1900)

await page.goto(`${baseUrl}/dashboard`, { waitUntil: 'networkidle' })
await injectPromoChrome(page)
await setCaption(page, 'T1D Companion', 'Understand what usually happens in real life. Built for personal insight, not medical replacement.')
await wait(2200)

const video = page.video()
await context.close()
await browser.close()

const rawPath = await video.path()
const finalWebm = path.join(outDir, 't1d-companion-promo.webm')
await rename(rawPath, finalWebm)
console.log(finalWebm)
