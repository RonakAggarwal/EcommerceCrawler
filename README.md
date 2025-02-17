# EcommerceCrawler
This is the basic crawler that takes a list of Ecommerce domains and tries to find all the products available on the given domains.

# Command to run the crawler
scrapy crawl ecommerce_crawler -a domains=list_of_domains_separated_by_comma -o product_urls.json

