from playwright.sync_api import sync_playwright
import time
import os

FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sunday.mp3")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")
USER_PROMPT = "piano"

def highlight_click(page, x, y, duration=500):
    page.evaluate("""([x, y, duration]) => {
        const dot = document.createElement('div');
        dot.style.position = 'fixed';
        dot.style.left = x + 'px';
        dot.style.top = y + 'px';
        dot.style.width = '30px';
        dot.style.height = '30px';
        dot.style.background = 'red';
        dot.style.border = '4px solid yellow';
        dot.style.borderRadius = '50%';
        dot.style.transform = 'translate(-50%, -50%)';
        dot.style.pointerEvents = 'none';
        dot.style.zIndex = '2147483647';
        document.body.appendChild(dot);
        setTimeout(() => dot.remove(), duration);
    }""", [x, y, duration])
    time.sleep(duration / 1000 + 0.1)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,             channel='chrome'  # or 'msedge' on Windows
)
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        print(page.viewport_size)
        # # --- FULL FLOW (upload from scratch) ---
        # page.goto("https://aidemos.meta.com/segment-anything/editor/segment-audio")
        # time.sleep(1)
        # print(page.title())
        # width = page.viewport_size['width']
        # height = page.viewport_size['height']

        # # 1. click accept
        # accept_cordsp = (.5, .65)
        # accept_cords = (width * accept_cordsp[0], height * accept_cordsp[1])
        # highlight_click(page, *accept_cords)
        # page.mouse.click(*accept_cords)
        # time.sleep(.1)

        # # 2. upload file - use file chooser
        # upload_cords = (855, 300)
        # highlight_click(page, *upload_cords)
        
        # with page.expect_file_chooser() as fc_info:
        #     page.mouse.click(*upload_cords)
        # file_chooser = fc_info.value
        # file_chooser.set_files(FILE_PATH)
        # print(f"Uploaded: {FILE_PATH}")
        
        # # 3. wait for upload to finish - URL will change to include media_id
        # print("Waiting for upload to complete...")
        # page.wait_for_url("**/segment-audio/?media_id=*", timeout=60000)
        # print(f"Upload complete! New URL: {page.url}")
        # # --- END FULL FLOW ---
        
        # --- TEST FLOW (pre-uploaded media) ---
        page.goto("https://aidemos.meta.com/segment-anything/editor/segment-audio/?media_id=865501006073861")
        time.sleep(1)
        print(page.title())
        width = page.viewport_size['width']
        height = page.viewport_size['height']
        
        # click accept dialog
        accept_cordsp = (.5, .65)
        accept_cords = (width * accept_cordsp[0], height * accept_cordsp[1])
        highlight_click(page, *accept_cords)
        page.mouse.click(*accept_cords)
        time.sleep(.1)
        # --- END TEST FLOW ---
        
        # 1. prompt the box
        input_cords = (220, 255)
        highlight_click(page, *input_cords)
        page.mouse.click(*input_cords)
        time.sleep(0.1)
        
        page.keyboard.type(USER_PROMPT)
        print(f"Typed prompt: {USER_PROMPT}")
        page.keyboard.press("Enter")
        
        # wait for processing to complete - "Add sound effects" appears when done
        print("Waiting for processing to complete...")
        page.wait_for_selector("text=Add sound effects", timeout=120000)
        print("Processing complete!")

        # create output dir if not exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 2. download all 3 files (need to reopen dialog each time)
        download_button_cords = (1245, 52)
        download_options = [
            (856, 437, "isolated_sound.wav"),
            (856, 387, "without_isolated_sound.wav"),
            (856, 337, "combined_audio.wav"),
        ]
        
        for x, y, filename in download_options:
            # open download dialog
            highlight_click(page, *download_button_cords)
            page.mouse.click(*download_button_cords)
            time.sleep(.1)
            
            # click download option
            highlight_click(page, x, y)
            with page.expect_download() as download_info:
                page.mouse.click(x, y)
            download = download_info.value
            save_path = os.path.join(OUTPUT_DIR, filename)
            download.save_as(save_path)
            print(f"Saved: {save_path}")
            time.sleep(.1)
        
        print("All downloads complete!")

        #options - do another, download, reprompt
        time.sleep(2)
        
        browser.close()

if __name__ == "__main__":
    main()
