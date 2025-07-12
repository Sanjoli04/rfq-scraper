from playwright.async_api import async_playwright
import pandas as pd
import numpy as np
import datetime
from typing import List
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

class RFQScraper:
    def __init__(self,url):
        self.url = url
        self.browser = None
        self.page = None
        self.context = None 

    async def init_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless = True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def get_rfq_id(self, inquiry_url):
        page = await self.context.new_page()
        rfq_id_found = {"value": None}
        def handle_request(request):
            if "rfqId=" in request.url:
                parsed_url = urlparse(request.url)
                rfq_id = parse_qs(parsed_url.query).get("rfqId", [None])[0]
                if rfq_id:
                    rfq_id_found["value"] = int(rfq_id)
        page.on("request", handle_request)
        try:
            await page.goto(inquiry_url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)
            return rfq_id_found["value"]if rfq_id_found["value"] else np.nan
        except Exception as e:
            print(f"[ERROR] Timeout or failure for {inquiry_url}: {e}")
            return np.nan
        finally:
            await page.close()

    async def get_rfq_page_data(self, page_no):
        url = self.url + str(page_no)
        await self.page.goto(url)
        content = await self.page.content()
        soup = BeautifulSoup(content, "html.parser")
        rfqs = []
        for item in soup.select(".next-row.next-row-no-padding.alife-bc-brh-rfq-list__row"):
            tags = [tag.text.strip() for tag in item.select(".next-tag-body")]
            publish_time =self.decompose_tag(item.select_one(".brh-rfq-item__publishtime"),"span").text.strip() if item.select_one(".brh-rfq-item__publishtime") else np.nan
            rfq = {
                "Title": item.select_one(".brh-rfq-item__subject-link").text.strip(),
                "Buyer Name": item.select_one(".text").text.strip(),
                "Buyer Image": np.nan if item.select_one(".img") is None else item.select_one(".img").get("src"),
                "Inquiry Time":  publish_time,
                "Quotes Left": self.decompose_tag(item.select_one(".brh-rfq-item__quote-left"), "span").text.strip() if item.select_one(".brh-rfq-item__quote-left") else np.nan,
                "Country": self.decompose_tag(item.select_one(".brh-rfq-item__country"), "span").text.strip() if item.select_one(".brh-rfq-item__country") else np.nan,
                "Quantity Required": item.select_one(".brh-rfq-item__quantity-num").text.strip(),
                "Email Confirmed": "Yes" if "Email Confirmed" in tags else "No",
                "Experienced Buyer": "Yes" if "Experienced buyer" in tags else "No",
                "Complete Order via RFQ": "Yes" if "Complete order via RFQ" in tags else "No",
                "Typical Replies": "Yes" if "Typically replies" in tags else "No",
                "Interactive User": "Yes" if "Interactive user" in tags else "No",
                "Inquiry URL": "https:" + item.select_one(".brh-rfq-item__subject-link").get("href"),
                "Inquiry Date": self.get_date(publish_time) if publish_time else np.nan,
                "Scraping Date": self.get_date("Just now"),
            }
            rfqs.append(rfq)
        sema = asyncio.Semaphore(10)
        async def fetch_with_limit(rfq):
            async with sema:
                rfq_id = await self.get_rfq_id(rfq["Inquiry URL"])
                rfq["RFQ ID"] = rfq_id
        await asyncio.gather(*[fetch_with_limit(rfq) for rfq in rfqs])
        return rfqs

    async def scrape(self,max_pages = 101):
        all_data = []
        for page_no in range(1, max_pages):
            print(f"Fetching data from 📄 {page_no}")
            data = await self.get_rfq_page_data(page_no)
            if not data:
                print(f"No RFQs found on page {page_no}. Stopping the scrape.")
                break
            all_data += data
        await self.context.close()
        await self.browser.close()
        return all_data

    def decompose_tag(self, obj, tagname):
        for tag in obj.find_all(tagname):
            tag.decompose()
        return obj

    def get_date(self,date_str: str) -> str:
        if not isinstance(date_str, str):
            return np.nan
        date =None
        date_str = date_str.lower()
        if "just now" in date_str or "minutes before" in date_str or "hours before" in date_str:
            date = datetime.datetime.now()
        elif "days ago" in date_str:
            days=int(date_str.split()[0])
            date =  (datetime.datetime.now() - datetime.timedelta(days=days))
        elif "months ago" in date_str:
            months = int(date_str.split()[0])
            date = (datetime.datetime.now() - datetime.timedelta(days = 30* months))
        elif "years ago" in date_str:
            years = int(date_str.split()[0])
            date = (datetime.datetime.now() - datetime.timedelta(days = 365* years))
        return date.strftime("%d-%m-%Y")

    def save_to_csv(self,data: List, filename: str):
        columns = [
            "RFQ ID", "Title", "Buyer Name", "Buyer Image",
            "Inquiry Time", "Quotes Left", "Country",
            "Quantity Required", "Email Confirmed",
            "Experienced Buyer", "Complete Order via RFQ",
            "Typical Replies", "Interactive User",
            "Inquiry URL", "Inquiry Date", "Scraping Date"
        ]
        data = pd.DataFrame(data, columns=columns)
        data.to_csv(filename, index=False)
        print("Data Saved to CSV with file: {}".format(filename))

async def main():
    url = "https://sourcing.alibaba.com/rfq/rfq_search_list.htm?spm=a2700.8073608.1998677545.2.fe0465aa11X6WR&country=AE&recently=Y&page="
    rfq_scraper = RFQScraper(url)
    await rfq_scraper.init_browser()
    data = await rfq_scraper.scrape()
    rfq_scraper.save_to_csv(data,"alibaba_rfq_{}.csv".format(rfq_scraper.get_date("Just now")))

if __name__ == "__main__":
    asyncio.run(main())
