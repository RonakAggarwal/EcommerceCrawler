import scrapy
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from scrapy.selector import Selector
from webdriver_manager.chrome import ChromeDriverManager
from ..items import EcommerceProducts
from ..constants import CRAWLER_NAME, COLLECTION_LIST, PRODUCT_LIST, DOMAIN_ERROR
import logging

class EcommerceCrawler(scrapy.Spider):
    name = CRAWLER_NAME

    def __init__(self, domains=None, *args, **kwargs):
        super(EcommerceCrawler, self).__init__(*args, **kwargs)

        if not domains:
            raise ValueError(DOMAIN_ERROR)

        self.allowed_domains = [domain.strip() for domain in domains.split(",")]
        self.start_urls = [f"https://{domain}" for domain in self.allowed_domains]

        # setting up Selenium Webdriver
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  #Runing Chrome without opening a window
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("window-size=1920x1080")

            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        except Exception as e:
            logging.error(f"Error while setting up Selenium WebDriver: {e}")
            raise {"Error": f"Error while setting up Selenium WebDriver: {e}"}

        self.visited_collections = set()
        self.visited_products = set()

    def parse(self, response):
        """Extracting collection URLs dynamically based on thekeywords."""
        for link in response.css("a::attr(href)").getall():
            collection_url = response.urljoin(link)

            if any(keyword in collection_url for keyword in COLLECTION_LIST) and collection_url not in self.visited_collections:
                self.visited_collections.add(collection_url)
                yield scrapy.Request(url=collection_url, callback=self.parse_collections, dont_filter=True)

    def parse_collections(self, response):
        # Handling javascript infinite scrolling
        self.driver.get(response.url)
        time.sleep(3) #Waiting for collections page to load

        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Waiting for new items loading

                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break  # Stop when no new items to load
                last_height = new_height

            # Get the fully loaded page source and parse with Scrapy
            sel = Selector(text=self.driver.page_source)
            selectors = [f'a[href*="/{keyword}/"]::attr(href)' for keyword in PRODUCT_LIST]
            css_selector = ", ".join(selectors)
            product_links = sel.css(css_selector).getall()

            for link in product_links:
                product_url = response.urljoin(link.strip())
                if product_url not in self.visited_products:
                    self.visited_products.add(product_url)
                    product = EcommerceProducts()
                    product["domain"] = response.url.split("/")[2]
                    product["product_url"] = product_url
                    yield product

            # Handle pagination to scrape all products from all the pages
            next_page = sel.css('a[aria-label="Next page"], a[rel="next"], a:contains("Next")::attr(href)').get()
            if next_page:
                next_page_url = response.urljoin(next_page.strip())
                if next_page_url not in self.visited_collections:
                    self.visited_collections.add(next_page_url)
                    yield scrapy.Request(next_page_url, callback=self.parse_collections, dont_filter=True)
        except Exception as e:
            logging.error(f"Error while parsing collections: {e}")
            raise {"Error": f"Error while parsing collections: {e}"}

    def closed(self):
        """Close the Selenium WebDriver when the spider finishes."""
        self.driver.quit()
