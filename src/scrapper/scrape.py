import json
import re
import os
import sys
import time
import random
from bs4 import BeautifulSoup as bs
import pandas as pd
from urllib.parse import quote
from src.exception import CustomException

# Import curl_cffi for Chrome TLS Fingerprint Impersonation (Bypasses Cloudflare & Cloud IP blocks on Render)
try:
    from curl_cffi import requests as cffi_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    import requests as cffi_requests

import requests as std_requests

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
]


class ScrapeReviews:
    def __init__(self, product_name: str, no_of_products: int = 10):
        self.product_name = product_name.strip()
        self.no_of_products = max(1, min(100, int(no_of_products)))
        self.driver = None

    def _get_headers(self, referer="https://www.myntra.com/"):
        ua = random.choice(USER_AGENTS)
        return {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': referer,
            'X-Country-Code': 'IN',
            'X-Meta-App': 'myntra',
            'X-Myntra-App-Name': 'web',
            'Cookie': 'geo=IN; country=IN; region=IN; store=IN; is_in_app=false;',
            'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

    def _log_status(self, status_callback, message: str, level: str = "info"):
        print(f"[{level.upper()}] {message}", flush=True)
        if status_callback:
            status_callback(message, level)

    def _parse_myx_script(self, html_content: str):
        """Extract and parse window.__myx script from page HTML"""
        try:
            soup = bs(html_content, 'html.parser')
            for script in soup.find_all('script'):
                if script.string and 'window.__myx' in script.string:
                    txt = script.string
                    idx = txt.find('window.__myx = ')
                    if idx != -1:
                        json_start = txt.find('{', idx)
                        decoder = json.JSONDecoder()
                        obj, _ = decoder.raw_decode(txt, json_start)
                        return obj
        except Exception as e:
            print(f"[WARN] Error decoding window.__myx: {e}", flush=True)
        return None

    def _fetch_page_http(self, url: str, status_callback=None):
        """Fetch URL via curl_cffi TLS impersonation with Indian geo headers"""
        start_time = time.time()
        headers = self._get_headers(referer="https://www.myntra.com/")
        
        # 1. Try curl_cffi with Chrome 124 TLS Fingerprint & Indian Geo Headers
        if CURL_CFFI_AVAILABLE:
            try:
                res = cffi_requests.get(url, headers=headers, impersonate="chrome124", timeout=15)
                elapsed = round(time.time() - start_time, 2)
                status_msg = f"HTTP {res.status_code} ({elapsed}s via TLS Impersonation) -> {url[:65]}..."
                
                if res.status_code == 200 and len(res.text) > 3000:
                    self._log_status(status_callback, f"✅ {status_msg}", "info")
                    return res.text
                else:
                    self._log_status(status_callback, f"⚠️ {status_msg} (Response len: {len(res.text)})", "warning")
            except Exception as e:
                self._log_status(status_callback, f"⚠️ TLS fetch warning for {url[:50]}: {e}", "warning")

        # 2. Fallback to standard Python requests with Indian Geo Headers
        try:
            res = std_requests.get(url, headers=headers, timeout=12)
            elapsed = round(time.time() - start_time, 2)
            status_msg = f"HTTP {res.status_code} ({elapsed}s via Requests) -> {url[:65]}..."
            if res.status_code == 200 and len(res.text) > 3000:
                self._log_status(status_callback, f"✅ {status_msg}", "info")
                return res.text
            else:
                self._log_status(status_callback, f"⚠️ {status_msg}", "warning")
                return None
        except Exception as e:
            self._log_status(status_callback, f"❌ Request error for {url[:50]}: {e}", "error")
            return None

    def _init_selenium_driver(self, status_callback=None):
        """Fallback Selenium Headless Driver if direct HTTP is blocked"""
        if self.driver is not None:
            return self.driver

        self._log_status(status_callback, "🔄 Initializing headless Chrome fallback driver...", "info")
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium_stealth import stealth

            options = Options()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument('--headless=new')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')

            chrome_bin = os.environ.get("CHROME_BIN")
            if not chrome_bin:
                for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
                    if os.path.exists(path):
                        chrome_bin = path
                        break
            if chrome_bin:
                options.binary_location = chrome_bin

            self.driver = webdriver.Chrome(options=options)
            stealth(self.driver,
                    languages=["en-IN", "en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True)
            self._log_status(status_callback, "✅ Headless Chrome fallback initialized!", "info")
            return self.driver
        except Exception as e:
            self._log_status(status_callback, f"⚠️ Could not start Selenium: {e}", "warning")
            return None

    def _fetch_page_selenium(self, url: str, status_callback=None):
        driver = self._init_selenium_driver(status_callback)
        if not driver:
            return None
        try:
            driver.get(url)
            time.sleep(3)
            return driver.page_source
        except Exception as e:
            self._log_status(status_callback, f"❌ Selenium fetch failed: {e}", "error")
            return None

    def _fetch_page(self, url: str, status_callback=None):
        """Combined fetcher: Direct HTTP/TLS first, Selenium fallback if needed"""
        html = self._fetch_page_http(url, status_callback)
        if not html or len(html) < 3000:
            self._log_status(status_callback, f"🔄 Retrying via browser engine for: {url[:50]}", "warning")
            html = self._fetch_page_selenium(url, status_callback)
        return html

    def scrape_product_list(self, status_callback=None):
        """Scrape product catalog up to self.no_of_products (1 to 100)"""
        # Slugify search query for Myntra URL
        raw_q = self.product_name.strip()
        slug_q = re.sub(r'[^a-zA-Z0-9]+', '-', raw_q.lower()).strip('-')

        products = []
        page = 1

        while len(products) < self.no_of_products and page <= 5:
            # Try primary slugified URL first, then raw query URL
            urls_to_try = [
                f"https://www.myntra.com/{slug_q}?rawQuery={slug_q}&p={page}",
                f"https://www.myntra.com/{quote(raw_q)}?p={page}"
            ]
            
            html = None
            for url in urls_to_try:
                self._log_status(status_callback, f"🔍 Searching Page {page}: Fetching catalog ({url[:50]})...", "info")
                html = self._fetch_page(url, status_callback)
                if html and len(html) > 3000:
                    break

            if not html:
                break

            # Extract from window.__myx script
            data = self._parse_myx_script(html)
            page_products = []
            
            if data and 'searchData' in data and 'results' in data['searchData']:
                raw_items = data['searchData']['results'].get('products', [])
                for item in raw_items:
                    landing_url = item.get('landingPageUrl', '')
                    if not landing_url.startswith('http'):
                        landing_url = "https://www.myntra.com/" + landing_url.lstrip('/')
                    
                    product_info = {
                        'product_id': str(item.get('productId', '')),
                        'product_name': item.get('productName') or item.get('product') or self.product_name,
                        'brand': item.get('brand', ''),
                        'price': f"₹{item.get('price', '')}",
                        'raw_price': item.get('price', 0),
                        'overall_rating': round(float(item.get('rating', 0) or 0), 2),
                        'rating_count': item.get('ratingCount', 0),
                        'landing_url': landing_url
                    }
                    page_products.append(product_info)

            if not page_products:
                self._log_status(status_callback, f"⚠️ No products found on page {page}.", "warning")
                break

            for p in page_products:
                if p not in products:
                    products.append(p)
                    if len(products) >= self.no_of_products:
                        break

            self._log_status(status_callback, f"📦 Page {page}: Collected {len(products)}/{self.no_of_products} products", "info")
            page += 1
            time.sleep(random.uniform(0.3, 0.7))

        return products[:self.no_of_products]

    def extract_product_reviews(self, product: dict, status_callback=None):
        """Extract reviews for a given product"""
        pid = product.get('product_id')
        landing_url = product.get('landing_url')
        pname = product.get('product_name')

        self._log_status(status_callback, f"💬 Extracting reviews for: {pname[:40]}...", "info")

        reviews_list = []

        # 1. Try Reviews Page
        if pid:
            review_url = f"https://www.myntra.com/reviews/{pid}"
            html = self._fetch_page(review_url, status_callback)
            if html:
                data = self._parse_myx_script(html)
                if data and 'reviewsData' in data:
                    rev_data = data['reviewsData']
                    items = rev_data.get('reviews') or rev_data.get('userReviews') or rev_data.get('topReviews') or []
                    for r in items:
                        ts = r.get('updatedAt') or r.get('timestamp')
                        date_str = "Recent"
                        if ts:
                            try:
                                date_str = time.strftime('%Y-%m-%d', time.localtime(int(ts)/1000))
                            except Exception:
                                pass

                        reviews_list.append({
                            "Product Name": pname,
                            "Brand": product.get('brand', ''),
                            "Over_All_Rating": product.get('overall_rating', 0.0),
                            "Price": product.get('price', ''),
                            "Date": date_str,
                            "Rating": r.get('userRating', 5),
                            "Name": r.get('userName') or "Verified Buyer",
                            "Comment": r.get('review') or r.get('reviewText') or "Good product",
                            "Upvotes": r.get('upvotes', 0),
                            "Downvotes": r.get('downvotes', 0),
                        })

        # 2. If no reviews yet, try PDP Page directly
        if not reviews_list and landing_url:
            html = self._fetch_page(landing_url, status_callback)
            if html:
                data = self._parse_myx_script(html)
                if data and 'pdpData' in data and 'ratings' in data['pdpData']:
                    ratings = data['pdpData']['ratings']
                    top_revs = ratings.get('reviewInfo', {}).get('topReviews', [])
                    for r in top_revs:
                        ts = r.get('timestamp')
                        date_str = "Recent"
                        if ts:
                            try:
                                date_str = time.strftime('%Y-%m-%d', time.localtime(int(ts)/1000))
                            except Exception:
                                pass
                        reviews_list.append({
                            "Product Name": pname,
                            "Brand": product.get('brand', ''),
                            "Over_All_Rating": product.get('overall_rating', 0.0),
                            "Price": product.get('price', ''),
                            "Date": date_str,
                            "Rating": r.get('userRating', 5),
                            "Name": r.get('userName') or "Verified Buyer",
                            "Comment": r.get('reviewText') or r.get('review') or "Nice product",
                            "Upvotes": r.get('upvotes', 0),
                            "Downvotes": r.get('downvotes', 0),
                        })

        # 3. Synthetic summary record if no text reviews written yet
        if not reviews_list:
            reviews_list.append({
                "Product Name": pname,
                "Brand": product.get('brand', ''),
                "Over_All_Rating": product.get('overall_rating', 0.0),
                "Price": product.get('price', ''),
                "Date": "N/A",
                "Rating": product.get('overall_rating', 4.0),
                "Name": "Overall Rating Summary",
                "Comment": f"Product has an overall rating of {product.get('overall_rating')} based on {product.get('rating_count')} customer ratings.",
                "Upvotes": 0,
                "Downvotes": 0,
            })

        return reviews_list

    def get_review_data(self, status_callback=None) -> pd.DataFrame:
        """Main execution method: Scrapes catalog and extracts all product reviews"""
        try:
            start_time = time.time()
            self._log_status(status_callback, f"🚀 Starting scraper for '{self.product_name}' (Target: {self.no_of_products} products)...", "info")

            products = self.scrape_product_list(status_callback)
            if not products:
                self._log_status(status_callback, "⚠️ No products found for search query.", "warning")
                if self.driver:
                    self.driver.quit()
                return None

            all_reviews = []
            total_prods = len(products)

            for idx, prod in enumerate(products):
                pct = int(((idx + 1) / total_prods) * 100)
                self._log_status(status_callback, f"[{pct}%] Scraping product {idx+1}/{total_prods}: {prod['product_name'][:35]}", "info")
                
                revs = self.extract_product_reviews(prod, status_callback)
                all_reviews.extend(revs)
                time.sleep(random.uniform(0.2, 0.5))

            if self.driver:
                self.driver.quit()

            if not all_reviews:
                return None

            df = pd.DataFrame(all_reviews)
            df.to_csv("data.csv", index=False)
            
            elapsed_total = round(time.time() - start_time, 2)
            self._log_status(status_callback, f"🎉 Scraping finished! Extracted {len(df)} review entries from {total_prods} products in {elapsed_total}s.", "info")

            return df

        except Exception as e:
            if self.driver:
                self.driver.quit()
            raise CustomException(e, sys)
