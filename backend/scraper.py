from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import random

def get_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    # Hide webdriver flag
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    return driver

def random_sleep(min=1.5, max=3.0):
    time.sleep(random.uniform(min, max))

def scrape_amazon(query, driver):
    results = []
    try:
        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}&ref=nb_sb_noss"
        print(f"[Amazon] Fetching: {url}")
        driver.get(url)
        random_sleep(2, 4)

        # Check if blocked
        if "robot" in driver.title.lower() or "captcha" in driver.page_source.lower():
            print("[Amazon] CAPTCHA detected, skipping...")
            return results

        wait = WebDriverWait(driver, 10)
        
        # Try multiple selectors
        selectors = [
            '[data-component-type="s-search-result"]',
            '.s-result-item[data-asin]:not([data-asin=""])',
        ]
        
        items = []
        for sel in selectors:
            items = driver.find_elements(By.CSS_SELECTOR, sel)
            if items:
                print(f"[Amazon] Found {len(items)} items with selector: {sel}")
                break
        
        for item in items[:6]:
            try:
                # Product name
                name_els = item.find_elements(By.CSS_SELECTOR, 'h2 a span, h2 span')
                if not name_els:
                    continue
                name = name_els[0].text.strip()
                if not name:
                    continue

                # Price - try multiple selectors
                price = None
                price_selectors = [
                    '.a-price .a-offscreen',
                    '.a-price-whole',
                    '.a-color-price',
                ]
                for ps in price_selectors:
                    price_els = item.find_elements(By.CSS_SELECTOR, ps)
                    if price_els:
                        price_text = price_els[0].get_attribute('innerHTML') or price_els[0].text
                        price_text = price_text.replace('₹','').replace(',','').replace(' ','').strip()
                        # Extract numbers only
                        import re
                        nums = re.findall(r'\d+\.?\d*', price_text)
                        if nums:
                            price = float(nums[0])
                            break

                if not price:
                    continue

                # Rating
                rating = 'N/A'
                rating_els = item.find_elements(By.CSS_SELECTOR, '.a-icon-star-small .a-icon-alt, .a-icon-alt')
                if rating_els:
                    rating_text = rating_els[0].get_attribute('innerHTML')
                    import re
                    r = re.findall(r'\d+\.?\d*', rating_text)
                    rating = r[0] if r else 'N/A'

                # URL
                link = '#'
                link_els = item.find_elements(By.CSS_SELECTOR, 'h2 a')
                if link_els:
                    link = link_els[0].get_attribute('href')

                # Image
                img = ''
                img_els = item.find_elements(By.CSS_SELECTOR, '.s-image')
                if img_els:
                    img = img_els[0].get_attribute('src')

                results.append({
                    'search_query': query,
                    'platform': 'Amazon',
                    'name': name[:120],
                    'price': price,
                    'rating': rating,
                    'url': link,
                    'image_url': img
                })
                print(f"[Amazon] ✅ {name[:50]} — ₹{price}")

            except Exception as e:
                print(f"[Amazon] Item error: {e}")
                continue

    except Exception as e:
        print(f"[Amazon] Page error: {e}")
    
    print(f"[Amazon] Total scraped: {len(results)}")
    return results




def scrape_all(query):
    driver = get_driver()
    all_results = []
    try:
        all_results += scrape_amazon(query, driver)
        random_sleep(1, 2)
        # Flipkart scraping removed as requested
        # all_results += scrape_flipkart(query, driver)
        # Reliance Digital scraping removed as requested
    finally:
        driver.quit()
    return all_results