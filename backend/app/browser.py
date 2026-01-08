from playwright.async_api import async_playwright, Browser, Playwright
import asyncio
import os
import re
from pathlib import Path

SAM_URL = "https://aidemos.meta.com/segment-anything/editor/segment-audio"
VIEWPORT = {"width": 1280, "height": 720}

class BrowserManager:
    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
    
    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=False, channel='chrome')
        print("Browser started")
    
    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        print("Browser stopped")
    
    @property
    def browser(self) -> Browser:
        if not self._browser:
            raise RuntimeError("Browser not started")
        return self._browser
    
    async def upload_chunk_to_sam(self, file_path: str) -> str:
        context = await self.browser.new_context(viewport=VIEWPORT)
        page = await context.new_page()
        
        try:
            await page.goto(SAM_URL, wait_until='networkidle')
            
            viewport = page.viewport_size
            width = viewport["width"]
            height = viewport["height"]
            
            # wait for accept button and click it
            await asyncio.sleep(2)  # wait for dialog to appear
            accept_cordsp = (0.5, 0.65)
            accept_cords = (width * accept_cordsp[0], height * accept_cordsp[1])
            await page.mouse.click(*accept_cords)
            
            # wait for page to be ready after accepting
            await asyncio.sleep(3)
            
            # upload file
            upload_cords = (855, 300)
            async with page.expect_file_chooser(timeout=5000) as fc_info:
                await page.mouse.click(*upload_cords)
            file_chooser = await fc_info.value
            await file_chooser.set_files(file_path)
            
            # wait for URL to contain media_id
            await page.wait_for_url("**/segment-audio/?media_id=*", timeout=60000)
            
            # extract media_id from URL
            url = page.url
            match = re.search(r"media_id=(\d+)", url)
            if not match:
                raise Exception("Failed to extract media_id from URL")
            
            sam_media_id = match.group(1)
            return sam_media_id
            
        finally:
            await context.close()
    
    async def process_chunk_prompt(self, sam_media_id: str, prompt: str, output_dir: str, chunk_index: int) -> dict:
        context = await self.browser.new_context(viewport=VIEWPORT)
        page = await context.new_page()
        
        try:
            await page.goto(f"{SAM_URL}/?media_id={sam_media_id}", wait_until='networkidle')
            
            viewport = page.viewport_size
            width = viewport["width"]
            height = viewport["height"]
            
            # wait for accept dialog and click it
            await asyncio.sleep(2)
            accept_cordsp = (0.5, 0.65)
            accept_cords = (width * accept_cordsp[0], height * accept_cordsp[1])
            await page.mouse.click(*accept_cords)
            
            # wait for page to be ready
            await asyncio.sleep(3)
            
            # wait for audio to load and decode
            try:
                await page.wait_for_selector("canvas", timeout=30000)
                await asyncio.sleep(5)
            except:
                await asyncio.sleep(5)
            
            # click input box and type prompt
            input_cords = (220, 255)
            await page.mouse.click(*input_cords)
            await asyncio.sleep(0.1)
            
            await page.keyboard.type(prompt)
            await page.keyboard.press("Enter")
            
            # wait for processing to complete
            await page.wait_for_selector("text=Add sound effects", timeout=120000)
            
            # create output dir for this chunk (ensure parent dirs exist)
            chunk_output_dir = os.path.join(output_dir, f"chunk_{chunk_index}")
            os.makedirs(chunk_output_dir, parents=True, exist_ok=True)
            
            # download isolated and without_isolated files
            download_button_cords = (1245, 52)
            download_options = [
                (856, 387, "without_isolated.wav"),
                (856, 337, "isolated.wav"),
            ]
            
            outputs = {}
            for x, y, filename in download_options:
                # open download dialog
                await page.mouse.click(*download_button_cords)
                await asyncio.sleep(0.1)
                
                # click download option
                async with page.expect_download() as download_info:
                    await page.mouse.click(x, y)
                download = await download_info.value
                save_path = os.path.join(chunk_output_dir, filename)
                await download.save_as(save_path)
                
                key = filename.replace(".wav", "")
                outputs[key] = save_path
                await asyncio.sleep(0.1)
            
            return outputs
            
        finally:
            await context.close()


browser_manager = BrowserManager()
