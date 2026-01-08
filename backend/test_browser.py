from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        # Use your system's Chrome/Edge instead of Playwright's Chromium
        browser = p.chromium.launch(
            headless=False,
            channel='chrome'  # or 'msedge' on Windows
        )
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        
        print("Browser opened. You can interact with it now.")
        print("Press Ctrl+C to close.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nClosing browser...")
        
        browser.close()

if __name__ == "__main__":
    main()