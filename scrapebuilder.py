from core.scraper import Scraper
import time

jubileescraper = Scraper('jubilee', 'jubileetest.txt')
jubileescraper.scrape()
print ('first scrape successful')
time.sleep(30)
jubileescraper.scrape()
print ('second scrape successful')
exit()

