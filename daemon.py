import datetime
import json
import math
import socket
import time
import pause
from apscheduler.schedulers.background import BackgroundScheduler
from dateutil.parser import parse
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import utils

init_config = json.loads(open('config.json', 'r').read())
scheduler = BackgroundScheduler()
jobs = {}


def perform_snipe(item_id, max_bid, listing_dt):
    try:
        driver = Firefox()
        driver.get('https://www.shopgoodwill.com/SignIn')
        username_input = driver.find_element(By.ID, 'txtUserName')
        username_input.send_keys(init_config['username'])
        password_input = driver.find_element(By.ID, 'txtPassword')
        password_input.send_keys(init_config['password'])

        password_input.send_keys(Keys.RETURN)
        time.sleep(5)

        driver.get('https://www.shopgoodwill.com/Item/' + str(item_id))

        minimum_bid = float(driver.find_element(By.XPATH,
                                                '/html/body/app-root/app-layout/main/div/app-detail/div/div[2]/div['
                                                '2]/div/div[1]/div[2]/div[2]/div[2]/p').get_attribute(
            'innerHTML')[1:])
        bid_amount = math.ceil(minimum_bid)

        pause.until(listing_dt - datetime.timedelta(seconds=init_config['added_to_bid']))

        while bid_amount <= max_bid:
            bid_input = driver.find_element(By.ID, 'currentBid')
            bid_input.send_keys('{:.2f}'.format(round(bid_amount, 2)))

            driver.find_element(By.XPATH,
                                '/html/body/app-root/app-layout/main/div/app-detail/div/div[2]/div[2]/div/div[1]/div['
                                '2]/button').click()
            driver.find_element(By.XPATH,
                                '/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup/form/p'
                                '-dialog/div/div/div[3]/button[2]').click()
            if driver.find_element(By.XPATH,
                                   '/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup/form'
                                   '/p-dialog/div/div/div[2]/div[2]/div/div/p[1]').get_attribute('innerHTML').find(
                                    'You have already been outbid.') >= 0:
                print('outbid')
                break
            else:
                driver.find_element(By.XPATH,
                                    '/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup'
                                    '/form/p-dialog/div/div/div[3]/button').click()
                print('bid placed')
                bid_amount += 1
    except Exception as e:
        print("Sniping item #" + str(item_id) + " failed")
        print(e)
    else:
        print("sniped item #" + str(item_id))


def add_job(listing):
    listing_dt = parse(listing['ending_dt'])
    job_dt = listing_dt - datetime.timedelta(minutes=1, seconds=init_config['bid_before_seconds'])
    job = scheduler.add_job(perform_snipe, 'date', run_date=job_dt,
                            args=[listing['item_id'], listing['max_bid'], listing_dt], id=str(listing['item_id']))
    jobs[str(listing['item_id'])] = {'job': job, 'listing': listing}


def load_jobs():
    conn, c = utils.get_conn()
    c.execute('SELECT * FROM listings')
    listings = c.fetchall()
    for listing in listings:
        # print(listing['name'])
        add_job(listing)
    c.close()
    conn.close()


def remove_jobs():
    for job_entry in list(jobs.values()):
        job_entry['job'].remove()
    jobs.clear()


load_jobs()
scheduler.start()

while True:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', init_config['port']))
        s.listen()
        conn, addr = s.accept()
        with conn:
            data = conn.recv(1024)
            if not data:
                continue
            msg = data.decode('ascii')
            if msg == 'close':
                scheduler.shutdown()
                exit()
            elif msg == 'update':
                remove_jobs()
                load_jobs()
            elif msg == 'dump':
                job_list = list(jobs.items())
                job_list.sort(key=lambda job: job[1]['job'].next_run_time)
                for key, value in job_list:
                    print('Job for item #' + key + ' scheduled to run at ' + str(
                        value['job'].next_run_time) + ' | ' + str(
                        value['listing']['name'] + ' | Max Bid: ' + str(value['listing']['max_bid'])))
