import json
import math
import time
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

init_config = json.loads(open('config.json', 'r').read())

item_id = '114648379'
max_bid = 7

try:
    driver = Firefox()
    driver.get('https://www.shopgoodwill.com/SignIn')

    time.sleep(5)
    # driver.find_element_by_css_selector('.cc-btn.cc-dismiss').click()

    username_input = driver.find_element(By.ID, 'txtUserName')
    username_input.send_keys(init_config['username'])
    password_input = driver.find_element(By.ID, 'txtPassword')
    password_input.send_keys(init_config['password'])

    password_input.send_keys(Keys.RETURN)
    # haven't decided if return key or button click is more stable
    # driver.find_element(By.XPATH, '/html/body/app-root/app-sign-in/main/div/div/div[1]/div/button').click()
    time.sleep(5)
    driver.get('https://www.shopgoodwill.com/Item/' + str(item_id))

    minimum_bid = float(driver.find_element(By.XPATH,
                                            '/html/body/app-root/app-layout/main/div/app-detail/div/div[2]/div['
                                            '2]/div/div[1]/div[2]/div[2]/div[2]/p').get_attribute(
        'innerHTML')[1:])
    # print(minimum_bid)
    bid_amount = math.ceil(minimum_bid)

    while bid_amount <= max_bid:
        bid_input = driver.find_element(By.ID, 'currentBid')
        bid_input.send_keys('{:.2f}'.format(round(bid_amount, 2)))

        driver.find_element(By.XPATH,
                            '/html/body/app-root/app-layout/main/div/app-detail/div/div[2]/div[2]/div/div[1]/div['
                            '2]/button').click()
        driver.find_element(By.XPATH,
                            '/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup/form/p'
                            '-dialog/div/div/div[3]/button[2]').click()
        # Below are some XPATHS that I used to debug the outbid issue
        # "/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup/form/p-dialog/div/div"
        # "/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup/form/p-dialog/div/div/div[2]/div[2]/div/div/p[1]"
        # "/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup/form/p-dialog/div/div/div[2]/div[2]/div/div/p[1]/p[1]"
        # "/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup/form/p-dialog/div/div/div[2]/div[2]/div/div/p[1]/h3"

        if driver.find_element(By.XPATH,
                               '/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup/form/p'
                               '-dialog/div/div/div[2]/div[2]/div/div/p[1]').get_attribute(
                                'innerHTML').find('You have already been outbid.') >= 0:
            print('outbid')
            break
        else:
            driver.find_element(By.XPATH,
                                '/html/body/app-root/app-layout/main/div/app-detail/div/app-confirm-bid-popup/form/p'
                                '-dialog/div/div/div[3]/button').click()
            print('bid placed')
            bid_amount += 1

except Exception as e:
    print("Sniping item #" + str(item_id) + " failed")
    print(e)
else:
    print("sniped item #" + str(item_id))
