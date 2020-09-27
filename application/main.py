# -*- coding: utf-8 -*-

import pymysql
import requests
from bs4 import BeautifulSoup

def lineNotify(message):
    url = 'https://notify-api.line.me/api/notify'
    token = 'xxxxxx'
    headers = {'content-type':'application/x-www-form-urlencoded','Authorization':'Bearer '+token}
    r = requests.post(url, headers = headers, data = {'stickerPackageId': 4, 'stickerId':274})
    r = requests.post(url, headers = headers, data = {'message':message, })
    print (r.text)

def insertDatabase(db, cursor, data):
    sql = "INSERT INTO tb_google_cloud_status (service_name, created_date, modified_date, message) \
                        VALUES (%s, %s, %s, %s)"
    val = (data['service_name'], 
            data['most-recent-update']['created'], 
            data['most-recent-update']['modified'], 
            data['most-recent-update']['text'])
    cursor.execute(sql, val)
    db.commit()

def updateDatabase(db, cursor, results, data):
    sql = "UPDATE tb_google_cloud_status SET modified_date = %s, message = %s WHERE id = %s"
    val = (data['most-recent-update']['modified'], 
            data['most-recent-update']['text'], 
            results[0][0])
    cursor.execute(sql, val)
    db.commit()

def main():
    request = requests.get(url='https://status.cloud.google.com/')
    soup = BeautifulSoup(request._content, "html.parser")
    table = soup.find_all("div", {"class": "timeline"})
    rows = []
    for tr in table[0].find_all('tr'):
        cols = []
        for td in tr.find_all(['td']):
            td_text = td.get_text(strip=True)
            bubble_ok = td.find_all(class_="end-bubble bubble ok")
            bubble_medium = td.find_all(class_="end-bubble bubble medium")
            bubble_high = td.find_all(class_="end-bubble bubble high")
            if len(td_text):
                cols.append(td_text)
            if len(bubble_ok):
                cols.append("Available")
            if len(bubble_medium):
                cols.append("Service Disruption")
            if len(bubble_high):
                cols.append("Service Outage")
        rows.append(cols)
    # notify service abnomal 
    for row in rows:
        if row and row[1] != "Available":
            # [TRUE] notify service abnomal only
            lineNotify("!!! UPDATE STATUS GCP !!! \n Service Name : [" +
                 row[0] + "] \n Status : [" + row[1] + "]")

    db = pymysql.connect("localhost", "root", "secret", "gcp")
    request = requests.get(url='https://status.cloud.google.com/incidents.json')
    for i in range(len(request.json())):
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tb_google_cloud_status WHERE service_name LIKE '%" + 
            request.json()[i]['service_name'] + "%' AND created_date LIKE '%" + 
            request.json()[i]['most-recent-update']['created'] + "%'")
        results = cursor.fetchall()
        # check new data from created date
        if (len(results) == 0):
            # [TRUE] notify and insert data
            insertDatabase(db, cursor, request.json()[i])
            lineNotify("!!! UPDATE INFOMATION !!! \n Service Name : [" + 
                request.json()[i]['service_name'] + "]\n Update Time : [" + 
                request.json()[i]['most-recent-update']['modified'] + "]\n" + 
                request.json()[i]['most-recent-update']['text'])
        else:
            # [FALSE] go check modified
            # check update data from modified date
            if (results[0][3] != request.json()[i]['most-recent-update']['modified']):
                # [TRUE] notify and update data
                updateDatabase(db, cursor, results, request.json()[i])
                lineNotify("!!! UPDATE INFOMATION !!! \n Service Name : [" + 
                    request.json()[i]['service_name'] + "]\n Update Time : [" + 
                    request.json()[i]['most-recent-update']['modified'] + "]\n" + 
                    request.json()[i]['most-recent-update']['text'])

if __name__ == '__main__':
    main()