from groq import Groq
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pandas as pd
from bs4 import BeautifulSoup
import time
import json
import re

# Initialize the Groq client
api_key = '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'  
client = Groq(api_key=api_key)

def get_google_search_urls(query, num_results=20):
    driver = init_driver()
    driver.get("https://www.google.com")

    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)
    driver.implicitly_wait(2)

    urls = []
    results = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
    urls.extend([result.get_attribute("href") for result in results])

    while len(urls) < num_results:
        try:
            next_button = driver.find_element(By.ID, "pnnext")
            next_button.click()
            driver.implicitly_wait(2)
            results = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
            urls.extend([result.get_attribute("href") for result in results])
        except Exception as e:
            print(f"Error navigating to the next page: {e}")
            break

    driver.quit()
    return urls[:num_results]

def init_driver():
    options = Options()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--incognito')
    driver = webdriver.Chrome(options=options)
    return driver

def extract_product_details(driver, url):
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        Price, Part_no, Details, Taxonomy, Product_Name, Cross_reference, Warranty = '', '', '', '', '', '', ''

        # Extraction logic (detailed and extensive)
        product_name_tags = ['h1','p','h3','div']
        for tag in product_name_tags:
            elements = soup.find_all(tag)
            for element in elements:
                cl = ["productName","product-title","stellar_phase_2","page_headers","page-title condensed js-product-name js-ga-product-name","x-item-title__mainTitle","product-detail-title","productTitle","titleSection"]
                if any(cls in element.get('id', '') for cls in cl) or any(cls in ' '.join(element.get('class', [])) for cls in cl):
                    Product_Name = element.get_text(strip=True)
                    break
            if Product_Name:
                break

        taxonomy_tags = ['div', 'a','ol','section']
        for tag in taxonomy_tags:
            elements = soup.find_all(tag)
            for element in elements:
                cl = ["page-bread-crumbs","breadcrumb","bread-crumbs","breadcrumnb","seo-breadcrumb-text","a-subheader a-breadcrumb feature","breadcrumbs","breadcrumb pull-left","site-breadcrumb js-site-breadcrumb"]
                if any(cls in ' '.join(element.get('class', [])) for cls in cl) or any(cls in element.get('id', '') for cls in cl):
                    Taxonomy = element.get_text(strip=True)
                    break
            if Taxonomy:
                break

        price_tags = ['p', 'div', 'span', 'li','h4','h3']
        for tag in price_tags:
            elements = soup.find_all(tag)
            for element in elements:
                cl = ["price", "msrp", "product-price","x-price-primary","corePriceDisplay_desktop_feature_div"]
                if any(cls in ' '.join(element.get('class', [])) for cls in cl) or any(cls in element.get('id', '') for cls in cl):
                    Price = element.get_text(strip=True)
                    break
            if Price:
                break

        part_no_tags = ['li','div','h5']
        for tag in part_no_tags:
            elements = soup.find_all(tag)
            for element in elements:
                cl = ["part_number","partNumSection","x-item-description-child","part-number","product_part-info"]
                if any(cls in ' '.join(element.get('class', [])) for cls in cl) or any(cls in element.get('id', '') for cls in cl):
                    Part_no = element.get_text(strip=True)
                    break
            if Part_no:
                break

        cross_reference_tags = ['ul']
        for tag in cross_reference_tags:
            elements = soup.find_all(tag)
            for element in elements:
                cl = ["list-unstyled cross-reference-list"]
                if any(cls in ' '.join(element.get('class', [])) for cls in cl) or any(cls in element.get('id', '') for cls in cl):
                    Cross_reference = element.get_text(strip=True)
                    break
            if Cross_reference:
                break

        detail_tags = ['p', 'div', 'span', 'li','table','dl']
        for tag in detail_tags:
            elements = soup.find_all(tag)
            for element in elements:
                cl = ["product-details", "details","productDetails_techSpec_section_1","product_info__description_list","tab-6","product-details-inner","description-collapse","specification-collapse","whyBuyThis"]
                if any(cls in ' '.join(element.get('class', [])) for cls in cl) or any(cls in element.get('id', '') for cls in cl):
                    Details = element.get_text(strip=True)
                    break
            if Details:
                break

        warranty_tags = ['p','div','li','ol']
        for tag in warranty_tags:
            elements = soup.find_all(tag)
            for element in elements:
                cl = ["WarrantyInfo-collapse","warranty"]
                if any(cls in ' '.join(element.get('class', [])) for cls in cl) or any(cls in element.get('id', '') for cls in cl):
                    Warranty = element.get_text(strip=True)
                    break
            if Warranty:
                break

        details = {
            'url': url,
            'Taxonomy': Taxonomy,
            'Product Name': Product_Name,
            'Part No': Part_no,
            'Cross Reference': Cross_reference,
            'Details': Details,
            'Warranty': Warranty,
            'price': Price
        }

        return details if any(details.values()) else None
    except Exception as e:
        print(f"Error extracting data from {url}: {e}")
        return None

def categorize_with_llm(product_details):
    messages = [
        {
            "role": "user",
            "content": f"Categorize the following product details into the fields 'url', 'Taxonomy', 'Product Name', 'Part No', 'Cross Reference', 'Details', 'price', 'Warranty' and return the result as a JSON object: {product_details}"
        }
    ]

    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192"
        )
        raw_response = response.choices[0].message.content.strip()
        print("LLM Raw Response:", raw_response)  # Print the raw response to debug

        # Clean the response to remove extra text
        clean_response = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if clean_response:
            categorized_data = json.loads(clean_response.group(0))
            return categorized_data
        else:
            print("No valid JSON found in LLM response.")
            return None
    except json.JSONDecodeError:
        print("Failed to decode LLM response as JSON.")
        return None
    except Exception as e:
        print(f"Error processing LLM response: {e}")
        return None

def price_comparison(query):
    driver = init_driver()
    urls = get_google_search_urls(query)
    product_details = []

    for url in urls:
        details = extract_product_details(driver, url)
        if details:
            categorized_info = categorize_with_llm(details)
            if categorized_info:
                product_details.append(categorized_info)

    driver.quit()

    if product_details:
        df = pd.DataFrame(product_details)
        df = df[['url', 'Taxonomy', 'Product Name', 'Part No', 'Cross Reference', 'Details', 'Warranty', 'price']]  # Ensure correct column order
        print(df)
        df.to_excel('./Datafile2.xlsx', index=False)
    else:
        print("No valid data extracted.")

if __name__ == "__main__":
    query = "AD1066 bracket"
    price_comparison(query)
