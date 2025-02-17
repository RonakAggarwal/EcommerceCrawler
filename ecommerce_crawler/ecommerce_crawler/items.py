# Define here the models for your scraped items
import scrapy


class EcommerceProducts(scrapy.Item):
    domain = scrapy.Field()
    product_url = scrapy.Field()
