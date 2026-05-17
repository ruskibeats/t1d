
import asyncio
from playwright.async_api import Playwright, async_playwright

async def run():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://192.168.0.92:3002")
        await page.screenshot(path="screenshot.png")
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
