from selenium import webdriver, common
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import numpy as np

import json
import os
import time

# example_URL = "https://www.cpwshop.com/camping/golden-gate-canyon-state-park/r/campsiteDetails.page?parkID=50025&siteID=1073&arvdate=06/16/2020&lengthOfStay=1"
DATES_BASE_URL = "https://www.cpwshop.com/camping/golden-gate-canyon-state-park/r/campsiteDetails.page?parkID="
SITES_BASE_URL = "https://www.cpwshop.com/camping/map-of-golden-gate-canyon-state-park/r/campgroundMap.page?parkID="
PARK_ID = '50025'
SITE_ID = '1073'
START_DATE, END_DATE = '6/15/2020', '6/28/2020'

def parse_dates(park_id, site_id, start_date, end_date):
	'''
	scrapes the avilability of 'site_id' between the start and end dates.  

	INPUTS: 
		park_id:    Park ID number (str)    Ex '50025'
		site_id:    Site ID number (str)    Ex '1073'
		start_date: Date (%d/%m/%Y, str)    Ex: '6/15/2020'
		end_date:   Date (%d/%m/%Y, str)    Ex: '6/28/2020'
	RETURNS: 
		dates_dict:  {'date':'available'}
	'''

	length_of_stay = 1

	# driver = webdriver.Chrome('chromedriver',chrome_options=chrome_options) #<-- if IN COLAB
	driver = webdriver.Chrome(os.path.abspath("drivers/chromedriver2")) #<-- if LOCAL
	
	def page_generator():
		date_range = pd.date_range(start = start_date, end = end_date).strftime('%m/%d/%Y')
		for arrival_date in date_range:
			page_info = {
				'url': DATES_BASE_URL + park_id + "&siteID=" + site_id + "&arvdate=" + arrival_date + "&lengthOfStay=" + str(length_of_stay),
				'date': arrival_date,
				}
			yield page_info

	page_gen = page_generator()

	dates_dict = {}
	while True: # loop until the generator is exhausted
		try: 
			page = next(page_gen)
			# load URL_parser
			driver.get(page['url'])
			content = driver.page_source
			# scrape the whole page
			soup = BeautifulSoup(content, features = "html.parser")
			# locate our target span within our target div
			calendarGrid = soup.body.find('div', attrs = {'id':'calendarGrid'})
			first_span = calendarGrid.find('span', recursive=False)

			# check the contents of our target span
			if first_span.a:
				dates_dict[page['date']] = 'available'
			elif first_span.text == "R":
				dates_dict[page['date']] = 'reserved'
			else: 
				dates_dict[page['date']] = 'unknown'
		except StopIteration:
			break
	driver.quit()

	return dates_dict



def get_valid_sites():
	'''
	scrapes the valid 'site_id's and relevant site info (only for a single park)  

	INPUTS: (none)
	RETURNS: 

		sites_dict:  {
			'1164': {
				pets_allowed': Boolean,
				'site_type': 'Basic',
				}
			(...)
			}
	'''

	URL = SITES_BASE_URL + PARK_ID + "&tab=sites#"
	print(URL, "\n", "Starting scrape...")

	# driver = webdriver.Chrome('chromedriver',chrome_options=chrome_options) #<-- if IN COLAB
	driver = webdriver.Chrome(os.path.abspath("drivers/chromedriver2")) #<-- if LOCAL

	driver.get(URL)

	sites = {}
	next_exists = True
	page = 0
	while next_exists:
		page += 1
		print(f"\nPage #{page}...")
		# scrape the whole page
		content = driver.page_source
		soup = BeautifulSoup(content, features = "html.parser")
		# loop through the target <tr>'s
		for tr in soup.body.find_all('tr', attrs = {'name':'e_Glow'}):
			# grab the site_id
			site_id_block = tr.td.div.contents[5] # i.e. the 6th child within the first 'div' within the first 'td' within 'tr'
			site_id = site_id_block.attrs['id'][9:]
			# check for pets allowed
			pets_allowed = False 
			for child in tr.contents[5].descendants:
				try: 
					if child.attrs['title'] == "Pets Allowed":
						pets_allowed = True
				except: 
					pass
			# load the info into the sites dict
			sites[site_id] = {
				'pets_allowed': pets_allowed,
				'site_type': tr.contents[2].text,
			}
		# move to the next page
		try: 
			time.sleep(1)
			button = driver.find_element_by_css_selector('a.link.standard.btnNext.hidden-xs.pagingButton')
			button.click()
		except common.exceptions.NoSuchElementException as err:
			next_exists = False
			print("no more pages.")
		time.sleep(1)

	driver.quit()
	return sites



if __name__ == '__main__':
	# print(f"\n\nScraping campsite availabilities for Park#{PARK_ID}, Site#{SITE_ID}, between {START_DATE} and {END_DATE}...")
	# dates_dict = parse_dates(PARK_ID, SITE_ID, START_DATE, END_DATE)
	# for key in dates_dict:
	# 	print("\t",key, dates_dict[key])

	sites = get_valid_sites()
	for key in sites:
		print(key, ":", sites[key])
	



