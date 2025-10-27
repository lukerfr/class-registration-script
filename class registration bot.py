import re
import html
import time
import requests
import warnings
from bs4 import BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


# some necessary stuff for errors and debugging
options = Options()
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options = options)
cert = "/Users/luke/charles-ssl-proxying-certificate.pem"

# opens a window, finds the login, and inputs user and pass
driver.get("https://sis.portal.nyu.edu/psp/ihprod/EMPLOYEE/EMPL/?cmd=start")
username_input = driver.find_element(By.ID, "username")
password_input = driver.find_element(By.ID, "password")

username_input.send_keys("user")
password_input.send_keys('pass')
password_input.send_keys(Keys.RETURN)

# waits until login finishes
element = WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.ID, "dont-trust-browser-button"))
)

element.click()

time.sleep(10)

cookies = {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}
user_agent = driver.execute_script("return navigator.userAgent;")

driver.close()

session = requests.Session()
session.cookies.update(cookies)

def update_headers(headers, session=session):
    session.headers.update(headers)

start_session_url = "https://sis.portal.nyu.edu/psc/ihprod/EMPLOYEE/EMPL/s/WEBLIB_IS_COPS.ISCRIPT1.FieldFormula.IScript_GetCRefContentUrl?CRefID=NYU_IS_ED_CS_ADD_TO_CART"
load_cart_url = "https://sis.nyu.edu/psc/csprod/EMPLOYEE/SA/c/SA_LEARNER_SERVICES_2.NYU_SSENRL_CART_FL.GBL?Page=NYU_SSENRL_CART_FL&Action=A&STRM=1254&ICAREER=UGRD&STRM=1254&ACAD_CAREER=UGRD&EMPLID=UGRD&INSTITUTION=NYUNV&PTPN_POPUP_WINDOW=N"
get_cart_url = "https://sis.nyu.edu/psc/csprod/EMPLOYEE/SA/c/SA_LEARNER_SERVICES_2.NYU_SSENRL_CART_FL.GBL?PTPN_POPUP_WINDOW=N"
enroll_url = 'https://sis.nyu.edu/psc/csprod/EMPLOYEE/SA/c/SA_LEARNER_SERVICES_2.NYU_SSENRL_ADD_FL.GBL?PTPN_POPUP_WINDOW=N'
cookie_string = "; ".join([f"{key}={value}" for key, value in cookies.items()])

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Connection': 'keep-alive',
    'Cookie': cookie_string,
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://sis.portal.nyu.edu/psp/ihprod/EMPLOYEE/EMPL/h/?tab=IS_SSS_TAB&jsconfig=IS_ED_SSS_SUMMARYLnk',
}

headers_load_cart = {
    'Referer' : 'https://sis.portal.nyu.edu/',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Dest': 'iframe',
    'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
}

response_start_session = session.get(start_session_url, verify=cert, headers=headers)

update_headers(headers_load_cart)

response_load_cart = session.get(load_cart_url, verify=cert, headers=headers)

soup = BeautifulSoup(response_load_cart.text, 'html.parser')
icsid = soup.find('input', {'name':'ICSID'})['value']
payload_get_cart = {
    'ICAJAX': '1',
    'ICAction': 'DERIVED_REGFRM1_LINK_ADD_ENRL',
    'ICSID' : icsid,
    'P_SELECT$0' : 'Y',
    'P_SELECT$1' : 'Y'
    # other payload fields
}

payload_results = {
    'ICAJAX' : 1,
    'ICStateNum' : 3,
    'ICAction' : 'DERIVED_REGFRM1_SSR_PB_SUBMIT',
    'ICSID' : icsid
}

response_get_cart = session.post(get_cart_url, headers=headers, data=payload_get_cart, verify=cert) #################

soup = BeautifulSoup(response_get_cart.text, 'xml')
pattern = r"https://sis\.nyu\.edu/psc/csprod/EMPLOYEE/SA/c/SA_LEARNER_SERVICES_2\.NYU_SSENRL_ADD_FL\.GBL\?[^']+"

for script in soup.find_all('GENSCRIPT', {'id': 'onloadScript'}):
    decoded_text = html.unescape(script.text)
    if 'ENRL_REQUEST_ID' in decoded_text:
        match = re.search(pattern, decoded_text)

if match:
    ref_url = match.group(0)
else:
    print("URL NOT FOUND")
update_headers({'Referer':load_cart_url})

load_enroll = session.get(ref_url, headers=headers, verify=cert)
update_headers({'Referer':ref_url})

response_enroll = session.post(enroll_url, headers=headers, data=payload_results, verify=cert) ##################
soup = BeautifulSoup(response_enroll.text, 'lxml')

for result in soup.find_all(lambda tag: tag.name == 'div' and 'ps-htmlarea' in tag.get('class', [])):
    if result and "Error:" in result.text:
        print(result.text.strip())
    elif result and "Success" in result.text:
        print("registered!")