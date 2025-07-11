# 🛠️ Alibaba RFQ Scraper

This project is a Python-based scraper for extracting RFQ (Request for Quotation) listings from Alibaba's sourcing platform. It uses **Playwright** (or optionally `selenium-wire`) to handle dynamic content and capture AJAX requests to extract hidden `rfqId`s.

## ✨ Features

- Extracts titles, buyer info, country, quantity, and timestamps.
- Captures network requests to fetch hidden `rfqId`s.
- Asynchronous scraping for speed and efficiency.
- Automatically saves all data to a clean CSV file.
- Supports headless browser mode for fast, silent operation.

## ⚙️ Requirements

- Python 3.11+
- Google Chrome installed (if using Selenium)
- Dependencies: `playwright`, `pandas`, `bs4`, `numpy`

## 🚀 Setup

```bash
git clone https://github.com/Sanjoli04/rfq-scraper.git
cd rfq-scraper
uv pip install -r requirements.txt  # or pip install -r requirements.txt
playwright install
```