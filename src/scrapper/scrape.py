from flask import request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium_stealth import stealth
from src.exception import CustomException
from bs4 import BeautifulSoup as bs
import pandas as pd
import os, sys
import time
import random
from selenium.webdriver.chrome.options import Options
from urllib.parse import quote


class ScrapeReviews:
    def __init__(self,
                 product_name:str,
                 no_of_products:int):
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--remote-debugging-port=0')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Randomize user-agent to avoid detection
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        options.add_argument(f'--user-agent={random.choice(user_agents)}')

        # Exclude automation-related switches
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # --- Proxy Support (ScraperAPI) ---
        # Set SCRAPER_API_KEY env var on Render to enable proxy routing
        scraper_api_key = os.environ.get("SCRAPER_API_KEY")
        if scraper_api_key:
            proxy = f"http://scraperapi:{scraper_api_key}@proxy-server.scraperapi.com:8001"
            options.add_argument(f'--proxy-server={proxy}')
            print(f"[INFO] Using ScraperAPI proxy for anti-bot bypass")

        # --- Auto-detect Chrome/Chromium binary ---
        chrome_bin = os.environ.get("CHROME_BIN")
        if not chrome_bin:
            for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
                if os.path.exists(path):
                    chrome_bin = path
                    break
        
        if chrome_bin:
            print(f"[INFO] Using Chrome binary: {chrome_bin}")
            options.binary_location = chrome_bin
        else:
            print("[INFO] No custom Chrome binary found, using default Chrome")

        # Start Chrome
        print("[INFO] Starting Chrome driver...")
        self.driver = webdriver.Chrome(options=options)
        print("[INFO] Chrome driver started successfully!")

        # Apply selenium-stealth to avoid bot detection
        stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
        )
        print("[INFO] Stealth mode applied!")

        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })

        self.product_name = product_name
        self.no_of_products = no_of_products

    def _random_delay(self, min_sec=2, max_sec=5):
        """Add random delay to mimic human behavior"""
        time.sleep(random.uniform(min_sec, max_sec))

    def scrape_product_urls(self, product_name):
        try:
            search_string = product_name.replace(" ","-")

            encoded_query = quote(search_string)
            url = f"https://www.myntra.com/{search_string}?rawQuery={encoded_query}"
            print(f"[INFO] Navigating to: {url}")
            
            self.driver.get(url)
            self._random_delay(4, 7)  # Random wait to mimic human
            
            myntra_text = self.driver.page_source
            print(f"[DEBUG] Page source length: {len(myntra_text)} chars")
            
            myntra_html = bs(myntra_text, "html.parser")
            pclass = myntra_html.findAll("ul", {"class": "results-base"})
            print(f"[DEBUG] Found {len(pclass)} result containers")

            product_urls = []
            for i in pclass:
                href = i.find_all("a", href=True)

                for product_no in range(len(href)):
                    t = href[product_no]["href"]
                    product_urls.append(t)

            print(f"[INFO] Found {len(product_urls)} product URLs")
            return product_urls

        except Exception as e:
            raise CustomException(e, sys)

    def extract_reviews(self, product_link):
        try:
            productLink = "https://www.myntra.com/" + product_link
            print(f"[INFO] Extracting reviews from: {productLink}")
            self.driver.get(productLink)
            self._random_delay(3, 6)
            
            prodRes = self.driver.page_source
            prodRes_html = bs(prodRes, "html.parser")
            title_h = prodRes_html.findAll("title")

            self.product_title = title_h[0].text

            overallRating = prodRes_html.findAll(
                "div", {"class": "index-overallRating"}
            )
            for i in overallRating:
                self.product_rating_value = i.find("div").text
            price = prodRes_html.findAll("span", {"class": "pdp-price"})
            for i in price:
                self.product_price = i.text
            product_reviews = prodRes_html.find(
                "a", {"class": "detailed-reviews-allReviews"}
            )

            if not product_reviews:
                print(f"[WARN] No review link found for: {self.product_title}")
                return None
            return product_reviews
        except Exception as e:
            raise CustomException(e, sys)
        
    def scroll_to_load_reviews(self, max_scrolls=10):
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            scroll_count = 0
            while scroll_count < max_scrolls:
                self.driver.execute_script("window.scrollBy(0, 1000);")
                self._random_delay(2, 4)
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    break
                
                last_height = new_height
                scroll_count += 1
        except Exception as e:
            print(f"Scroll interrupted (this is okay, continuing with loaded reviews): {e}")



    def extract_products(self, product_reviews: list):
        try:
            t2 = product_reviews["href"]
            Review_link = "https://www.myntra.com" + t2
            self.driver.get(Review_link)
            
            self.scroll_to_load_reviews()
            
            review_page = self.driver.page_source

            review_html = bs(review_page, "html.parser")
            review = review_html.findAll(
                "div", {"class": "detailed-reviews-userReviewsContainer"}
            )

            for i in review:
                user_rating = i.findAll(
                    "div", {"class": "user-review-main user-review-showRating"}
                )
                user_comment = i.findAll(
                    "div", {"class": "user-review-reviewTextWrapper"}
                )
                user_name = i.findAll("div", {"class": "user-review-left"})

            reviews = []
            for i in range(len(user_rating)):
                try:
                    rating = (
                        user_rating[i]
                        .find("span", class_="user-review-starRating")
                        .get_text()
                        .strip()
                    )
                except:
                    rating = "No rating Given"
                try:
                    comment = user_comment[i].text
                except:
                    comment = "No comment Given"
                try:
                    name = user_name[i].find("span").text
                except:
                    name = "No Name given"
                try:
                    date = user_name[i].find_all("span")[1].text
                except:
                    date = "No Date given"

                mydict = {
                    "Product Name": self.product_title,
                    "Over_All_Rating": self.product_rating_value,
                    "Price": self.product_price,
                    "Date": date,
                    "Rating": rating,
                    "Name": name,
                    "Comment": comment,
                }
                reviews.append(mydict)

            print(f"[INFO] Extracted {len(reviews)} reviews for: {self.product_title}")

            review_data = pd.DataFrame(
                reviews,
                columns=[
                    "Product Name",
                    "Over_All_Rating",
                    "Price",
                    "Date",
                    "Rating",
                    "Name",
                    "Comment",
                ],
            )

            return review_data

        except Exception as e:
            raise CustomException(e, sys)
        
    
    def skip_products(self, search_string, no_of_products, skip_index):
        product_urls: list = self.scrape_product_urls(search_string, no_of_products + 1)

        product_urls.pop(skip_index)

    def get_review_data(self) -> pd.DataFrame:
        try:
            product_urls = self.scrape_product_urls(product_name=self.product_name)

            if not product_urls:
                self.driver.quit()
                print("[WARN] No products found for the given search query.")
                return None

            product_details = []

            review_len = 0


            while review_len < self.no_of_products and review_len < len(product_urls):
                product_url = product_urls[review_len]
                review = self.extract_reviews(product_url)

                if review:
                    product_detail = self.extract_products(review)
                    product_details.append(product_detail)

                    review_len += 1
                else:
                    product_urls.pop(review_len)

            self.driver.quit()

            if not product_details:
                print("[WARN] No review data collected from any product.")
                return None

            data = pd.concat(product_details, axis=0)
            
            data.to_csv("data.csv", index=False)
            
            print(f"[INFO] Total reviews scraped: {len(data)}")
            return data

        except Exception as e:
            raise CustomException(e, sys)
