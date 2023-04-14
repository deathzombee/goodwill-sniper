import json
import re
import socket
import sqlite3
import pytz
from dateutil.parser import parse
from selenium.webdriver import Firefox
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from tzlocal import get_localzone

init_config = json.loads(open('config.json', 'r').read())


def get_conn():
    conn = sqlite3.connect('sniper.db')
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()


def send_msg(msg):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('localhost', init_config['port']))
        s.sendall(msg.encode('ascii'))


def retreive_listing_information(item_id):
    options = FirefoxOptions()
    options.add_argument('-headless')
    driver = Firefox(options=options)
    driver.get('https://www.shopgoodwill.com/Item/' + str(item_id))

    driver.find_element(By.CSS_SELECTOR, '.cc-btn.cc-dismiss').click()

    name = driver.find_element(By.CSS_SELECTOR, '.mb-4').get_attribute('innerHTML')
    ending_dt_raw = driver.find_element(By.CSS_SELECTOR, '.item-info-box').get_attribute('innerHTML')
    driver.quit()

    pattern = re.compile("(.[0-9][0-9]/.*)PT")
    matcher = pattern.search(ending_dt_raw)
    print(matcher.group(1))
    ending_dt_str = matcher.group(1)
    ending_dt = parse(ending_dt_str)
    tz = pytz.timezone('US/Pacific')
    ending_dt = tz.localize(ending_dt)
    ending_dt = ending_dt.astimezone(get_localzone())
    ending_dt = ending_dt.replace(tzinfo=None)

    return {'name': name, 'ending_dt': ending_dt}
