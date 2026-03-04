import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        page = await browser.new_page()
        try:
            print("Going to quotes.toscrape.com...")
            await page.goto("http://quotes.toscrape.com/js/", timeout=5000)
            print("Loaded!")
            content = await page.content()
            print("Content length:", len(content))
        except Exception as e:
            print("Error:", repr(e))
        finally:
            await browser.close()

asyncio.run(run())
