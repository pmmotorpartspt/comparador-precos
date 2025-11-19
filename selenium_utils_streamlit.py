# -*- coding: utf-8 -*-
"""
Selenium utils para Streamlit Cloud
Usa Chromium instalado pelo sistema
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def build_driver(headless=True):
    """Cria driver para Streamlit Cloud"""
    options = Options()
    
    if headless:
        options.add_argument("--headless")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1400,950")
    
    # Usar chromium do sistema
    options.binary_location = "/usr/bin/chromium"
    service = Service("/usr/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(35)
    
    return driver
