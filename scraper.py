
from bs4 import BeautifulSoup
import requests
import smtplib
import zipfile
import urllib
import os, shutil
import json

def webscrape():
	#Error handling if FAA website has changed
	try:
		#Open table on FAA website conataining Chart data
		sectionalData = buildSectional()
		url = 'http://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/vfr/?viewType=Print&viewClass=Print'
		response = requests.get(url)
		html = response.text
		soup = BeautifulSoup(html, 'lxml')
		table = soup.find(class_='striped')
		table.find_all('tr')

		#Put city,version and download link into temp file
		map_data = []

		downloader = urllib.URLopener()
		i = 0
		for row in table.find_all('tr')[1:]:
			col = row.find_all('td')
			city = col[0].get_text().strip()
			link = col[1].find('a').get('href')
			sectional = sectionalData[i]
			i += 1
			version = col[1].get_text().split()
			version[4] = version[4][0:4]
			startDate = ' '.join(version[2:5])
			version = version[0].strip()

			m = col[2].get_text().split()
			m[4] = m[4][0:4]
			endDate = ' '.join(m[2:5])

			filePath = "./"+ sectional +"/"+ version +"/"
			fileName = filePath + sectional + version + ".zip"

			if os.path.isdir("./"+ sectional):
				for file in os.listdir("./"+ sectional):
					if version in file:
						break
					else:
						shutil.rmtree("./"+ sectional)
						break

			if not os.path.isdir(filePath):
				os.mkdir(sectional, 0o777)
				os.mkdir(sectional +"/"+ version, 0o777)
				downloader.retrieve(link, fileName)

				unzip = zipfile.ZipFile(fileName, 'r')
				unzip.extractall(filePath)
				unzip.close()

				os.remove(fileName)

				tifFileName = ""
				for file in os.listdir(filePath):
					if file.endswith(".tif"):
						tifFileName = file
				gdalFileName = filePath + tifFileName

				zipname = filePath + sectional + ".zip"
				tileWithGDAL(gdalFileName, filePath, zipname)

				modelfile = open(filePath + sectional +"model.json", 'w+')
				modelfile.truncate()
				model = {
					'city' : city,
					'version' : version,
					'publicationDate' : startDate,
					'expirationDate' : endDate,
					'regionId' : sectional
				}

				json_model = json.dumps(model)
				modelfile.write(json_model)
				modelfile.close
				
	except Exception as e:
		print(e)
		return

# A .tif should exist in the file path when this is called.
def tileWithGDAL(fName, fPath, zipName):
	os.system("gdal_translate -of vrt -expand rgba '"+ fName +"' '"+ fPath +"translated.vrt'")
	os.system("gdal2tiles.py -p 'raster' '"+ fPath +"translated.vrt'")
	for file in os.listdir(fPath):
		if os.path.isfile(os.path.join(fPath, file)):
			os.remove(os.path.join(fPath, file))
	os.chmod('translated', 0o777)

	zipf = zipfile.ZipFile(zipName, 'w', zipfile.ZIP_DEFLATED)
	for root, dirs, files in os.walk('translated/'):
		if root == "translated/":
			dirs[:] = [d for d in dirs if any(strings in d for strings in ('4','5','6'))]
		for file in files:
			if 'openlayers.html' not in file and 'tilemapresource.xml' not in file:
				zipf.write(os.path.join(root, file), os.path.join(root, file)[11:])
	shutil.rmtree('./translated')

def buildSectional():
	url = 'https://www.faa.gov/air_traffic/flight_info/aeronav/productcatalog/vfrcharts/sectional/'
	response = requests.get(url)
	html = response.text
	soup = BeautifulSoup(html, 'lxml')
	table = soup.find(class_='striped')
	table.find_all('tr')
	sectional = []
	for row in table.find_all('tr')[1:]:
		col = row.find_all('td')
		sectional.append(col[1].string.strip()[1:])
	return sectional

webscrape()