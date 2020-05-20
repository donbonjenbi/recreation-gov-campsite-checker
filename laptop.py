from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd
import os


driver = webdriver.Chrome(os.path.abspath("drivers/chromedriver2"))


products=[] #List to store name of the product
prices=[] #List to store price of the product
ratings=[] #List to store rating of the product
driver.get("https://www.flipkart.com/laptops/pr?sid=6bo,b5g")


content = driver.page_source
soup = BeautifulSoup(content, features = "html.parser")

count = 0
for a in soup.findAll('a',href=True, attrs={'class':'_31qSD5'}):
	name=a.find('div', attrs={'class':'_3wU53n'})
	price=a.find('div', attrs={'class':'_1vC4OE _2rQ-NK'})
	rating=a.find('div', attrs={'class':'hGSR34'})
	
	products.append(name.text)
	prices.append(price.text)
	try: 
		ratings.append(rating.text)
	except: 
		rating = BeautifulSoup("<div></div>", features = "html.parser").find('div')
		ratings.append(rating.text)
	print("\n\n", count, "name: ", name.text, "price: ", price.text, "rating: ", rating.text)

df = pd.DataFrame({'Product Name':products,'Price':prices,'Rating':ratings}) 
df.to_csv('flipkart_laptops.csv', index=False, encoding='utf-8')




