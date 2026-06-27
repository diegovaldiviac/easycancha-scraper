from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("https://www.easycancha.com")
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    print(soup.title.text if soup.title else "No title found")


if __name__ == "__main__":
    main()
