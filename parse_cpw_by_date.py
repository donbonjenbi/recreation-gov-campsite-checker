from selenium import webdriver, common
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

import json
import os
import time

# example_URL = "https://www.cpwshop.com/camping/golden-gate-canyon-state-park/r/campsiteDetails.page?parkID=50025&siteID=1073&arvdate=06/16/2020&lengthOfStay=1"
DATES_BASE_URL = "https://www.cpwshop.com/camping/golden-gate-canyon-state-park/r/campsiteDetails.page?parkID="
SITES_BASE_URL = "https://www.cpwshop.com/camping/map-of-golden-gate-canyon-state-park/r/campgroundMap.page?parkID="
PARKS_BASE_URL = "https://www.cpwshop.com/camping"
PARK_ID = '50025'
SITE_ID = '1073'
START_DATE, END_DATE = '6/15/2020', '6/30/2020'

# driver = webdriver.Chrome('chromedriver',chrome_options=chrome_options) #<-- if IN COLAB
driver = webdriver.Chrome(os.path.abspath("drivers/chromedriver-2")) #<-- if LOCAL



def parse_dates(site_id, start_date, end_date, base_url = DATES_BASE_URL + PARK_ID, ):
	'''
	scrapes the avilability of 'site_id' between the start and end dates.  

	INPUTS: 
		park_id:    Park ID number (str)    Ex '50025'
		site_id:    Site ID number (str)    Ex '1073'
		start_date: Date (%d/%m/%Y, str)    Ex: '6/15/2020'
		end_date:   Date (%d/%m/%Y, str)    Ex: '6/28/2020'
	RETURNS: 
		dates_dict:  {
			'date':'available'
			[...]
			}
	'''

	length_of_stay = 1
	
	date_range = pd.date_range(start = start_date, end = end_date).strftime('%m/%d/%Y')
	base_url = base_url.replace('campground', 'campsite')
	
	def page_generator():
		i = -1
		for date in date_range:
			url = base_url + "&siteID=" + site_id + "&arvdate=" + date + "&lengthOfStay=" + str(length_of_stay)
			i += 1
			yield url, date, i

	page_gen = page_generator()

	dates_dict = {}
	while True: # loop until the date generator is exhausted
		try: 
			url, date, i = next(page_gen)
			# if we need a new page, get it
			j = i % 14
			if j == 0:
				driver.get(url)
				content = driver.page_source
				# scrape the whole page
				soup = BeautifulSoup(content, features = "html.parser")
				skip = False
				try: 
					# locate our target span within our target div
					calendarGrid = soup.body.find('div', attrs = {'id':'calendarGrid'})
					# first_span = calendarGrid.find('span', recursive=False)
					spans = calendarGrid.find_all('span', recursive=False)
				except: 
					print("Error occurred when looking for 'calendarGrid' or 'spans'. Waiting 1 sec and trying again...")
					time.sleep(1)
					content = driver.page_source
					soup = BeautifulSoup(content, features = "html.parser")
					calendarGrid = soup.body.find('div', attrs = {'id':'calendarGrid'})
					spans = calendarGrid.find_all('span', recursive=False)
				# finally: 
				# 	skip = True
				# 	print("Could not find 'spans' in 'calendarGrid'. Skipping...") 

			# check the contents of our target span
			if not skip: 
				if spans[j].a:
					dates_dict[date] = 'available'
				elif spans[j].text == "R":
					dates_dict[date] = 'reserved'
				else: 
					dates_dict[date] = 'unknown'
			else: 
				dates_dict[date] = 'unknown'
		except StopIteration:
			break

	return dates_dict



def get_valid_sites(base_url = SITES_BASE_URL + PARK_ID):
	'''
	scrapes the valid 'site_id's and relevant site info (only for a single park)  

	INPUTS: (none)
	RETURNS: 

		sites_dict = {
			'1164': {
				pets_allowed': Boolean,
				'site_type': 'Basic',
				}
			(...)
			}
	'''

	URL = base_url + "&tab=sites#"
	print(URL, "\n", "Starting sites scrape...")

	driver.get(URL)

	sites = {}
	next_page_exists = True
	page = 0
	while next_page_exists:
		page += 1
		print(f"Page #{page}...")
		# scrape the whole page
		content = driver.page_source
		soup = BeautifulSoup(content, features = "html.parser")
		# loop through the target <tr>'s
		for tr in soup.body.find_all('tr', attrs = {'name':'e_Glow'}):
			# grab the site_id
			try: 
				site_id_block = tr.td.div.contents[5] # i.e. the 6th child within the first 'div' within the first 'td' within 'tr'
				site_id = site_id_block.attrs['id'][9:]
				
				# check for pets allowed
				pets_allowed = False 
				try :
					for child in tr.contents[5].descendants:
						try: 
							if child.attrs['title'] == "Pets Allowed":
								pets_allowed = True
						except: 
							pass
				except:
					print(f"Error checking pets for site {site_id}. assuming 'false' and moving on...")
					pass
				
				# check site type
				try: 
					site_type = tr.contents[2].text
				except: 
					site_type = 'unknown'
					print(f"Error checking 'type' for site {site_id}. Recording 'unknown' and moving on....")
					pass
				
				# load the info into the sites dict
				sites[site_id] = {
					'pets_allowed': pets_allowed,
					'site_type': site_type,
				}	
			except: 
				# ----------
				# 
				# 	TODO:   add alt formatting for sites that don't follow the normal structure. 
				# 			example is site 'centennial GPA' on page 4 of this park:  https://www.cpwshop.com/camping/jackson-lake-state-park/r/campgroundDetails.page?parkID=50028&tab=sites#
				# 			There's also one on page 5 of this park.  
				# 
				# -----------
				print(f"Error checking site number. (the one after #{site_id}) Skipping this site...")
				pass
		# move to the next page
		try: 
			time.sleep(1)
			button = driver.find_element_by_css_selector('a.link.standard.btnNext.hidden-xs.pagingButton')
			button.click()
		except common.exceptions.NoSuchElementException as err:
			next_page_exists = False
			print("no more pages.\n")
		time.sleep(1.5)

	# driver.quit()
	return sites



def get_valid_parks():
	'''
	finds the full list of valid parks and their URLs

	INPUTS: 
		(none)

	OUTPUTS:  
		parks_dict = {
			'Steamboat Lake State Park, CO' : {
				'url' : string
			}
			[...]
		}

	'''
	URL = PARKS_BASE_URL + ".page#"
	print(URL, "\n", "starting parks scrape...")

	driver.get(URL)

	parks = {}
	next_page_exists = True
	page = 1
	while next_page_exists:
		print(f"Page #{page}...")

		check_next_park = True
		
		while check_next_park:
			
			# scrape the whole page
			content = driver.page_source
			soup = BeautifulSoup(content, features = "html.parser")

			# loop through the target elements
			for tr in soup.body.find_all('tr', attrs = {'name':'e_Glow'}):
				# find the target span
				span = tr.td.div.contents[10] # can also try [8,9] if [10] fails
				
				# get the park name
				park_name = span.a.text

				# if this is a new park
				if park_name not in parks:
					try: 
						# follow the link
						time.sleep(1)
						button = driver.find_element_by_id(span.a.attrs['id'])
						button.click()
						time.sleep(1)
						# store the park name & URL
						parks[park_name] = {
							'url': driver.current_url
							}
						print(f"\t{park_name} is new. adding it... ({driver.current_url})")
						# go back to the original page
						backlink = driver.find_element_by_id("backlink")
						backlink.click()
						time.sleep(1.5)
						page = 1
						print("\nPage #1...")
						# exit the for loop
						break
					except common.exceptions.ElementNotInteractableException as err:
						print(err)
				else: 
					# do nothing (continue to the next tr)
					pass
			# if we've looped through the whole park list on this page...
			else: 
				# exit the while loop
				check_next_park = False

		# move on to next page
		try: 
			time.sleep(1)
			button = driver.find_element_by_css_selector('a.link.standard.btnNext.hidden-xs.pagingButton')
			button.click()
			page += 1
		except common.exceptions.NoSuchElementException as err:
			next_page_exists = False
			print("no more pages.")
		time.sleep(1)

	# driver.quit()
	return parks



def save_json(data_dict, filename):
	with open(filename, 'w') as file:
		json.dump(data_dict, file)
	file.close()
	print(f"Saved data to file: {filename}.")



def load_json(filename):
	with open(filename, 'r') as file:
		data = json.load(file)
	file.close()
	print(f"loading data from file: {filename}...")
	return data



def update_parks_list(save_path = 'parks.json'):
	parks = get_valid_parks()
	for key in parks:  #37 keys, 321 sec
		print(key, ":", parks[key])
	print(len(parks), "parks total\n")
	save_json(parks, save_path)
	return parks



def update_sites_list(parks_load_path = 'parks.json', save_path = 'parks_and_sites.json'):
	parks = load_json(parks_load_path)
	for park in parks:
		sites = get_valid_sites(base_url = parks[park]['url'])
		parks[park]['sites'] = sites
	save_json(parks, save_path)
	return sites



def update_dates_data(data, start_date, end_date, save_filename, replace_existing = False):
	
	for park in data:

		print(park)
		park_url = data[park]['url']
		
		for site in data[park]['sites']:
			
			if replace_existing == False and 'dates' in data[park]['sites'][site]:
				print("\t", site, "- already finished. skipping")
				continue
			else: 
				print("\t", site)
				data[park]['sites'][site]['dates'] = parse_dates(site, start_date, end_date, base_url = park_url)

		save_json(data, filename)

	return data



def summarize(data, check_in, check_out):
	
	first_park = data[next(iter(data))]
	first_site = first_park['sites'][next(iter(first_park['sites']))]
	available_dates = first_site['dates']
	if check_in not in available_dates.keys() or check_out not in available_dates.keys():
		print(f"\n\tERROR: we don't have data for those dates. Please choose a search window between {list(available_dates.keys())[0]} - {list(available_dates.keys())[-1]}, or scrape new data. \n")
		return

	print(f"\n\nParks with openings for check-in on {check_in} & check-out on {check_out}...")
	# print(json.dumps(data, indent=4))

	summary = {}

	# FOR EACH PARK
	for park_name in data:

		site_type_totals = {}

		park_data = data[park_name]
		park_url = park_data['url']
		
		# FOR EACH SITE: 
		for site_num in park_data['sites']:
			site = park_data['sites'][site_num]

			# check this site type
			site_type = site['site_type']
			if site_type not in site_type_totals:
				site_type_totals[site_type] = 0

			# check if this site is availible during these dates
			date_range = pd.date_range(start = check_in, end = check_out).strftime('%m/%d/%Y')
			available = True
			for date in site['dates']:
				if date in date_range[:-1]:
					if site['dates'][date] != 'available':
						available = False
			if available:
				site_type_totals[site_type] += 1

		is_full = True
		for site_type in site_type_totals:
			if site_type_totals[site_type] != 0:
				is_full = False


		summary[park_name] = {
			'totals': site_type_totals,
			'is_full': is_full,
			'url': park_url,
		}

	# first print the available parks
	for park_name in summary:
		if summary[park_name]['is_full'] == False:
			print(f"\n\t{park_name[:-4]}:", end =" ")
			totals = summary[park_name]['totals']
			for site_type in totals:
				if totals[site_type] != 0:
					print(f"\n\t\t\t{totals[site_type]} '{site_type}'", end =" ")
					pass

	# then print the unavailable parks
	print(f"\n\nParks that are full for {check_in} - {check_out}...  ")
	for park_name in summary:
		if summary[park_name]['is_full'] == True:
			print(f"\t{park_name[:-4]}")



if __name__ == '__main__':

	# print(f"\n\nScraping campsite availabilities for all CO State parks, between {START_DATE} and {END_DATE}...\n")

	# parks = update_parks_list(save_path = 'parks.json')
	# parks_and_sites = update_sites_list(parks_load_path = 'parks.json', save_path = 'parks_and_sites.json')

	filename = 'allparks_' + START_DATE.replace('/','-') + '_to_' + END_DATE.replace('/','-') + '.json'
	data = load_json(filename)

	# data = update_dates_data(data, START_DATE, END_DATE, save_filename = filename, replace_existing = False):

	summarize(data, check_in = '06/17/2020', check_out = '06/20/2020')

	driver.quit()


	



