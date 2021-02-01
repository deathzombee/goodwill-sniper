import sqlite3
import json
import datetime
import pause
import utils
import math
import socket
from dateutil.parser import parse
from multiprocessing.connection import Listener
from selenium.webdriver import Firefox
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from apscheduler.schedulers.background import BackgroundScheduler

init_config = json.loads(open('config.json', 'r').read())
scheduler = BackgroundScheduler()
jobs = {}

def perform_snipe(item_id, max_bid, listing_dt):
    try:
        driver = Firefox()
        driver.get('https://www.shopgoodwill.com/SignIn')

        username_input = driver.find_element_by_id('Username')
        username_input.send_keys(init_config['username'])
        password_input = driver.find_element_by_id('Password')
        password_input.send_keys(init_config['password'])
        driver.find_element_by_id('login-submit').click()

        driver.get('https://www.shopgoodwill.com/Item/' + str(item_id))

        minimum_bid = float(driver.find_element_by_css_selector('.minimum-bid').get_attribute('innerHTML')[1:])
        bid_amount = math.ceil(minimum_bid)

        driver.find_element_by_css_selector('.cc-btn.cc-dismiss').click()

        while True:
            bid_input = driver.find_element_by_id('bidAmount')
            bid_input.send_keys('{:.2f}'.format(round(bid_amount, 2)))

            pause.until(listing_dt - datetime.timedelta(seconds=init_config['added_to_bid']))

            driver.find_element_by_id('placeBid').click()
            driver.find_element_by_id('place-bid-modal').click()

            if driver.find_element_by_id('bid-result').get_attribute('innerHTML').find('You have already been outbid.') == -1:
                driver.find_element_by_css_selector('.modal-footer button.btn.btn-default').click()
                if bid_amount < max_bid:
                    continue
            
            break

    except Exception as e:
        print("Sniping item #" + str(item_id) + " failed")
        print(e)
    else:
        print("sniped item #" + str(item_id))

def add_job(listing):
    listing_dt = parse(listing['ending_dt'])
    job_dt = listing_dt - datetime.timedelta(minutes=1, seconds=init_config['bid_before_seconds'])
    job = scheduler.add_job(perform_snipe, 'date', run_date=job_dt, args=[listing['item_id'], listing['max_bid'], listing_dt], id=str(listing['item_id']))
    jobs[str(listing['item_id'])] = {'job': job, 'listing': listing}

def load_jobs():
    conn, c = utils.get_conn()
    c.execute('SELECT * FROM listings')
    listings = c.fetchall()
    for listing in listings:
        add_job(listing)
    c.close()
    conn.close()

def remove_jobs():
    for job_entry in list(jobs.values()):
        job_entry['job'].remove()
    jobs.clear()

load_jobs()
scheduler.start()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('localhost', init_config['port']))
    s.listen()
    conn, addr = s.accept()
    while True:
        msg = conn.recv(1024).decode('ascii')

        if msg == 'close':
            scheduler.shutdown()
            exit()
        elif msg == 'update':
            remove_jobs()
            load_jobs()