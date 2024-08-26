import email
import smtplib, ssl, csv, shutil

from typing import final
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select
# from selenium.webdriver.support import Expec
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
import config, json, time, sys, requests, re, subprocess, shutil, glob, tempfile, os
from os import path
import numpy as np
import scipy.interpolate as si
# from urllib import request

from seleniumOSC.Payment_Submission_Log import Payment_Submission_Log
from seleniumOSC.Selenium_Payments_Jobs_Log import Selenium_Payments_Jobs_Log
from datetime import date, datetime
from seleniumOSC import sqlconnector, email_alert, invoice_extract, driver_init

from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.headerregistry import Address
from email.utils import formataddr

dirname = path.dirname(path.dirname(path.abspath(__file__)))
cfg = config.Config(path.join(dirname, 'AP4\\etc\\var.cfg'))
from inspect import currentframe, getframeinfo

cf = currentframe()
filename = getframeinfo(cf).filename
# import pyautogui for screenshots
import pyautogui
import logging

# now we will Create and configure logger
current_datetime = datetime.now().strftime('%Y_%m_%d')
str_current_datetime = str(current_datetime)

port = 587
smtp_login = cfg['smtp_login']
smtp_server = cfg['smtp_server']
from_email = cfg['alert_email'].split('@')
password = cfg['alert_emailpw']
receiver = cfg['daily_email_receiver'].split('@')
payment_submission_count_csv_path = cfg['payment_submission_count_csv_path']
csv_results_path = f"LOGS/payment_submission_results/att/" + str_current_datetime + ".csv"


def initialize_logger(account_number):
    current_datetime = datetime.now().strftime('%Y_%m_%d')
    str_current_datetime = str(current_datetime)

    logger = logging.getLogger(account_number)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', '%m-%d-%Y %H:%M:%S')

    file_handler = logging.FileHandler("LOGS/invoicePayments/spectrum/" + account_number + "_" + str_current_datetime + ".log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Define path to CSV
csv_path = f"{cfg['att_payments_path']}ATT Test Accounts.csv"
csv_results_path = f"LOGS/payment_submission_results/att/" + str_current_datetime + ".csv"

print(csv_path)
public_screen_shot_path = cfg['public_screen_shot_path']

def agent_payment_submission_cycle_status_alert(success_count: int, total_count: int, failed_accounts: list, provider: str):
    print("sending payment submission email")
    print(success_count)
    print(total_count)
    print(failed_accounts)
    print(provider)
    filename = str_current_datetime + ".csv"
    message = EmailMessage()
    message['Subject'] = f"Selenium Payment Submissions Agent Status - {provider}  Result: {success_count}/{total_count}"
    message['From'] = Address("Selenium Payment Submission Agent Script", from_email[0], from_email[1])
    # message['To'] = Address("CIS", receiver[0], receiver[1])
    message['To'] = cfg['email_receiver']
    msg = f"""\tThe Selenium Payment Submission Script for {provider}  has completed running.
        Total of {success_count} out of {total_count} payments were made successfully.
        Below are the list of failed account numbers
        {failed_accounts}"""
    message.set_content(msg)

    # Attach the CSV file
    try:
        with open(csv_results_path, 'rb') as file:
            file_content = file.read()
        message.add_attachment(file_content, maintype='text', subtype='csv', filename=filename)
        print(f"Attached file {filename}")
    except Exception as e:
        print(f"Failed to attach file {csv_results_path}: {e}")
    with smtplib.SMTP(smtp_server) as server:
        server.starttls()
        server.login(cfg['smtp_login'], password)
        server.send_message(message)

def att_payment_submission(payment_data, driver, temp_dir):
    # Starting the payment submission process
    print("ATT payment submission Starting")
    print(payment_data)
    print("Payment made:")
    payment_made = None
    payment_submission_log = None
    print(payment_made)

    # Extract variables from payment data
    account_number = payment_data[0]
    amount = payment_data[1]
    service_provider = payment_data[2]
    cvv = payment_data[3]
    username = account_number
    cc_number = payment_data[5][0]
    cc_exp_month = payment_data[5][1]
    exp_year = payment_data[5][2]
    last_four_cc = payment_data[6]
    user = payment_data[7]
    zip_code = payment_data[8]

    # Print extracted variables
    print(f"Account Number: {account_number}")
    print(f"Amount: {amount}")
    print(f"Service Provider: {service_provider}")
    print(f"CVV: {cvv}")
    print(f"Username: {username}")
    print(f"Credit Card Number: {cc_number}")
    print(f"Credit Card Expiration Month: {cc_exp_month}")
    print(f"Credit Card Expiration Year: {exp_year}")
    print(f"Last Four of CC: {last_four_cc}")
    print(f"User: {user}")

    expiration_date = f"{cc_exp_month}/{exp_year[-2:]}"

    # Get the logger for this account
    logger = initialize_logger(account_number)

    logger.info("::::ATT PAYMENT AGENT BEING RUN ::::")
    logger.info(f"Running on account {account_number}")
    logger.info(f"Amount being paid {amount}")
    logger.info(f"User making the payment {user}")

    # Print log information
    print(f"Logger Info: Running on account {account_number}")
    print(f"Logger Info: Amount being paid {amount}")
    print(f"User making the payment: {user}")

    # Selenium Logic
    # driver = webdriver.Chrome(options=options)

    print("Opening webpage")
    driver.get("https://www.att.com/acctsvcs/fastpay")
    driver.maximize_window()
    driver.implicitly_wait(5)
    wait = WebDriverWait(driver, 10)
    time.sleep(2)
    looksgood_clicked = False
    logger.info("ATT PAYMENT SCREEN LOADED")

    time.sleep(1)
    # POP UP LAND
    try:
        cookies_pop_up = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'acceptAccept')))
        if cookies_pop_up:
            cookies_pop_up.click()
        else:
            new_cookies_pop_up = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '/html/body/div[2]//div/div/div/div/div/div/div[2]/button[3]')))
            if new_cookies_pop_up:
                new_cookies_pop_up.click()
                looksgood_clicked = True
    except TimeoutException:
        pass

    if looksgood_clicked == False:
        if 'Interceptors' in driver.current_url:
            looksgood_button = wait.until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'Looks good')]")))
            time.sleep(5)
            looksgood_button.click()
            looksgood_clicked = True
    time.sleep(1)
    try:
        survey_close_button = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//button[@aria-label='Close dialog']")))
        survey_close_button.click()
    except TimeoutException:
        pass



    try:
        bill_pay_pop_up = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="Combined-Shape"]')))
        bill_pay_pop_up.click()
    except TimeoutException:
        pass



    # END POP UP LAND
    # Select User Type

    homeInternetSelectBox = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div[2]/div/div/div/div[3]/div[2]/div[5]/div/div/div/div[2]')))
    time.sleep(2)
    driver.execute_script("arguments[0].scrollIntoView(true);", homeInternetSelectBox)
    time.sleep(1)  # Give some time after scrolling
    homeInternetSelectBox.click()
    # Wait for the banner to disappear
    try:
        wait.until(EC.invisibility_of_element_located((By.ID, 'gpc-banner-container')))
        homeInternetSelectBox = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div[2]/div/div/div/div[3]/div[2]/div[5]/div/div/div/div[2]')))
        time.sleep(2)  # You might not need this delay, but keeping it might help with stability
        homeInternetSelectBox.click()
    except Exception as e:
        logger.error(f"Failed to click the homeInternetSelectBox: {str(e)}")
        driver.save_screenshot('error_screenshot.png')



    time.sleep(2)

    account_num = wait.until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="accountNumber"]')))

    time.sleep(2)
    account_num.send_keys(account_number)
    time.sleep(2)



    account_zip_code =  wait.until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="zipCode"]')))
    time.sleep(2)
    account_zip_code.send_keys(zip_code)
    time.sleep(2)

    print(" BOTH ZIP CODE AND ACCOUNT NUMBER INPUTS COMPLETE")
    continue_button = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div[2]/div/div/div/div[3]/div/div[2]/div/div/div[2]/button')))
    if continue_button:
        print("continue button found and its clickable")
        continue_button.click()

    # check for payment header
    payment_header = wait.until(EC.presence_of_element_located((By.XPATH, ' //*[@id="root"]/div/div[2]/div/div/div/div[1]/div[1]/h2')))
    if payment_header:
        print("you are in the payment details page")
        payment_amount_input = wait.until(EC.presence_of_element_located((By.XPATH, ' //*[@id="paymentAmount"]')))
        if payment_amount_input:
            print("payment total input found")
            payment_amount_input.send_keys(amount)
            # insert cc_number details
            payment_method =  wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div[2]/div/div/div/div[3]/div/div[2]/div/div/div[1]/div[4]/div[2]/div[1]')))
            time.sleep(2)
            driver.execute_script("arguments[0].scrollIntoView(true);", payment_method)
            time.sleep(1)
            try:
                wait.until(EC.invisibility_of_element_located((By.ID, 'gpc-banner-container')))
                payment_method =  wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div[2]/div/div/div/div[3]/div/div[2]/div/div/div[1]/div[4]/div[2]/div[1]')))
                if payment_method:
                    print("inserting cc details")
                    payment_method.click()

            except Exception as e:
                logger.error(f"Failed to click the homeInternetSelectBox: {str(e)}")
                driver.save_screenshot('error_screenshot.png')


    logger.info("PAYMENT DETAILS PAGE LOADED")
    card_number = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="Payment_CardInfo_CardNumber_TextBox"]')))
    time.sleep(3)
    card_number.send_keys(cc_number)
    time.sleep(3)

    expiration_date_input =  wait.until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="Expiration_Date_TextField"]')))


    expiration_date_input.send_keys(expiration_date)

    security_code_input =  wait.until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="Payment_CardInfo_CVV_TextBox"]')))
    time.sleep(3)
    security_code_input.send_keys(cvv)

    zip_code = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="Payment_CardInfo_ZipCode_TextBox"]')))
    time.sleep(3)
    zip_code.send_keys("27858")



    # //PAYMENT BUTTON
    try:
        pay_button = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="test_1"]/div/div[2]/div/div[5]/button')))
        if pay_button :
            print("FOUND PAY BUTTON..")

            pay_button.click()
            time.sleep(120)

    except TimeoutException:
        logger.error("Payment button not found")
        print("Payment button not found")
    try:
        success_text = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div[2]/div/div/div/div[2]/div/div[2]/div/div/div[1]/div/div[2]')))
        if success_text:
            print("found success text")
        payment_made = True
        driver.save_screenshot(
            'LOGS/screenshots/' + account_number + '_' + str_current_datetime + '.png')
    except TimeoutException:
        payment_made = False
        driver.save_screenshot(
            'LOGS/screenshots/' + account_number + '_' + str_current_datetime + '.png')
    try:
        transaction_id_element = wait.until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div[2]/div/div/div/div[2]/div/div[2]/div/div/div[2]/div[1]/div[2]')))
        transaction_id = transaction_id_element.text
        logger.info(("transaction_id"))
        logger.info(transaction_id)


    except TimeoutException:
        transaction_id = 000000

    if payment_made:
        print("payment made: ")
        print(payment_made)
        payment_submission_log = Payment_Submission_Log(str(account_number), str(amount), "att",
                                                        str(last_four_cc),
                                                        str(transaction_id), 1,
                                                        "none", str(driver.current_url), datetime.now())
    else:
        payment_submission_log = Payment_Submission_Log(str(account_number), str(amount), "att",
                                                        str(last_four_cc),
                                                        str(transaction_id), 0,
                                                        "Payment could not be made", str(driver.current_url),
                                                        datetime.now())

    payment_submission_date = datetime.now()
    with open(csv_results_path, 'a', newline='') as file:
        writer = csv.writer(file)
        writer = csv.writer(file)
        if file.tell() == 0:
            writer.writerow(['Account Number', 'Amount', 'Service Provider', 'Last Four CC', 'Transaction ID',
                             'Payment Submission Date', 'User Submitting'])
        writer.writerow(
            [account_number, amount, service_provider, last_four_cc, transaction_id, payment_submission_date, user])
    return payment_made, payment_submission_log


def run_agent(provider: str, headless, scheduler_ran) -> None:
    print("=======ATT PAYMENTS PROCESSING ")
    print(provider)
    print(headless)
    print(scheduler_ran)
    print("=======")
    # This is the list to keep track of failed account numbers
    failed_list: list = []
    # This is to keep track of the successful account numbers
    success_list: list = []
    # this is the variable to keep track of number of successful runs
    success_count: int = 0
    failure_count: int = 0


    with open(csv_path, mode='r', newline='', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            # Check if the row is empty or contains only empty strings
            if row and not all(map(lambda x: x == '', row)):
                print(row)
                if headless == True:
                    driver, temp_dir = driver_init.init_headless_driver()
                else:
                    driver, temp_dir = driver_init.init_nonheadless_driver()
                # os.system('cmd /c "taskkill /im chromedriver.exe /f"')

                vendor_description = row.get('Vendor Description')
                user_type = row.get('User Type')
                description_user = row.get('Description User')
                account_number = row.get('Account Number')
                zip_code = row.get('ZIP Code')
                last_four_cc = row.get('Last Four of CC')
                vendor_invoice_number = row.get('Vendor Invoice #')
                due_date = row.get('Due Date')
                amount = row.get('Amount')
                document_number = row.get('Document #')

                # Print statements for each variable
                print(f"Vendor Description: {vendor_description}")
                print(f"User Type: {user_type}")
                print(f"Description User: {description_user}")
                print(f"Account Number: {account_number}")
                print(f"ZIP Code: {zip_code}")
                print(f"Last Four of CC: {last_four_cc}")
                print(f"Vendor Invoice #: {vendor_invoice_number}")
                print(f"Due Date: {due_date}")
                print(f"Amount: {amount}")
                print(f"Document #: {document_number}")
                print("-" * 40)  # Separator between rows
                last_four_cc = "3791"
                cvv = "435"
                user_type = "home"
                user ="eddie"
                if len(account_number) < 8:
                    failed_list.append(account_number)
                    failure_count += 1
                    continue
                if len(cvv) < 3:
                    cvv = '0' + cvv
                payment_method = sqlconnector.get_payment_method(f"{cfg['payment_methods']}", last_four_cc, cvv)
                account_username = account_number
                # Convert amount to float and format it with two decimal places
                amount = amount.replace('$', '')  # Remove the dollar sign
                amount = amount.replace(',', '')  # Remove the comma
                amount = "{:.2f}".format(float(amount))  # Now convert to float
                # Get the logger for this account
                logger = initialize_logger(account_number)
                logger.info("initialized driver")
                payment_data = [account_number, amount, vendor_description, cvv, account_username, payment_method,
                                last_four_cc,user,zip_code]

                result, payment_log = att_payment_submission(payment_data, driver, temp_dir)
                print(result)
                print(payment_log)

                if result is not None and payment_log is not None:
                    success_list.append(account_number)
                    success_count += 1
                    success_log = sqlconnector.insert_to_payment_submission_logs_table(payment_log)
                    if success_log:
                        print("Successfully Log in SQL Table")
                    else:
                        print("Failure to input log into sql")
                else:
                    failed_list.append(account_number)
                    failure_count += 1
                    failure_log = sqlconnector.insert_to_payment_submission_logs_table(payment_log)
                    if failure_log:
                        print("Successfully Log in SQL Table")
                    else:
                        print("Failure to input log into sql")

                driver.quit()
                temp_dir.cleanup()
            else:
                print("Empty or invalid row encountered")
                continue
    total_count: int = success_count + failure_count
    failed_account_numbers = ', '.join(failed_list)
    print(f"Script has ended. There were {success_count} payments made out of {total_count}. Failed account numbers: {failed_account_numbers}")

    payments_job_log_data = Selenium_Payments_Jobs_Log('Spectrum', success_count, failure_count, total_count,
                                                       failed_account_numbers, datetime.now())
    payment_job_log = sqlconnector.insert_to_selenium_payment_jobs_table(payments_job_log_data)

    if payment_job_log:
        print("Payment Log was successfully inserted into SQL Table")
        logger.info("Payment Log was successfully inserted into SQL Table")
    else:
        print("Payment Log failed to be inserted into SQL Table")
        logger.info("Payment Log failed to be inserted into SQL Table")

    # email_alert.add_to_payment_submissions_count_csv("spectrum", success_count, total_count)

    agent_payment_submission_cycle_status_alert(success_count, total_count, failed_list, "spectrum")
    print(f"Number of successful transactions: {success_count}")
    print(f"Number of failed transactions: {failure_count}")
    print(f"Successful accounts: {success_list}")
    print(f"Failed accounts: {failed_list}")


if __name__ == "__main__":
    run_agent(provider="att", headless=False, scheduler_ran=False)
