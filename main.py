#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from ConfigParser import RawConfigParser
from monitor.monitor import GithubMonitor
from monitor.model import GithubDB
from monitor.reporter import Reporter
from jinja2 import Template, Environment, FileSystemLoader
from datetime import datetime
import json
import codecs
import logging
import schedule
import time
import sys
import re
import requests
import base64

logging.basicConfig(format="%(asctime)s [%(levelname)-8s] %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

parser = RawConfigParser()
parser.readfp(codecs.open("github_monitor.conf", "r", "utf-8"))
dbname = parser.get('Model Setting', 'dbname')
username = parser.get('Github Setting', 'username')
password = parser.get('Github Setting', 'password')
server = parser.get('Mail Setting', 'server')
port = parser.get('Mail Setting', 'port')
muser = parser.get('Mail Setting', 'username')
mpass = parser.get('Mail Setting', 'password')
companys = json.loads(parser.get('Monitor Settings', 'companys'))
keywords = json.loads(parser.get('Monitor Settings', 'keywords'))
filters = json.loads(parser.get('Monitor Settings', 'filters'))

gdbs = dict((c,GithubDB("dbs/"+dbname+"_"+c+".db")) for c in companys)
gmos = dict((c,GithubMonitor(username, password, gdbs[c])) for c in gdbs)
r = Reporter(muser, server, 25, muser, mpass)

[gmos[c].add_keywords_for_search(keywords[c]) for c in keywords]

def get_source_code(git_url):
    try:
        content = requests.get(git_url, auth=(username,password), timeout=60).content
        logger.info("GET " + git_url)
        gitjson = json.loads(content)
        result =  base64.b64decode(gitjson['content'])
    except KeyError as ee:
        result = ""
        logger.error(ee.message)
        logger.error(gitjson)
    except Exception as e:
        result = ""
        logger.error(e.message)
    return result

def job():
    for c in companys:
        gmos[c].update()

    today = datetime.today().strftime('%Y-%m-%d')
    attachfiles = []
    codes_count = {}
    new_codes_count = {}
    report_newdatas = {}

    for c in companys:

        newdatas = gdbs[c].get_new_datas()

        #github file content matching and adding the result to the report.
        for item in newdatas:
            item['regexp_match'] = []
            matches = filter(lambda words: re.search(words, get_source_code(item['git_url'])), filters.get(c, []))
            item['regexp_match'].extend(matches)

        for item in newdatas:
            item['sort_score'] = len(item['regexp_match']) + int(item['isnew'])

        report_newdatas.update({c:sorted(newdatas, key=lambda x: x['sort_score'], reverse=True)})

        todaydatas = gdbs[c].get_recent_datas()

        codes_count.update({c: len(newdatas)})
        new_codes_count.update({c: len(filter(lambda x: x['isnew'], report_newdatas[c]))})

        nd_filename = u"saves/github_new_codes_{company}_{date}.html".format(
            date=today, company=c
        )
        td_filename = u"saves/github_today_codes_{company}_{date}.html".format(
            date=today, company=c
        )
        report_filename = u"saves/github_report_codes_{company}_{date}.html".format(
            date=today, company=c
        )

        attachfiles.extend([nd_filename, td_filename])

        with codecs.open(nd_filename, "w+", 'utf-8') as f:
            with open('template/template1.html', 'r') as ff:
                template = Template(ff.read().decode('utf-8'))
                f.write(template.render(items=newdatas))

        with codecs.open(td_filename, "w+", 'utf-8') as f:
            with open('template/template1.html', 'r') as ff:
                template = Template(ff.read().decode('utf-8'))
                f.write(template.render(items=todaydatas))

        with codecs.open(report_filename, "w+", 'utf-8') as f:
            with open('template/template1.html', 'r') as ff:
                template = Template(ff.read().decode('utf-8'))
                f.write(template.render(items=report_newdatas[c]))

    with open("template/report_template.html", 'r') as f:
        template = Environment(loader=FileSystemLoader(u"saves/")).from_string(
            f.read().decode('utf-8')
        )
        mail_content = template.render(
            date = today,
            companys = companys,
            codes_count = codes_count,
            new_codes_count = new_codes_count,
            items = report_newdatas
        ).encode('utf-8')

    logger.info(attachfiles)

    r.alert("Github Monitor {date}".format(date=datetime.now().strftime("%Y-%m-%d")),
            mail_content,
            "xiaomingchi@sechnic.com",
            #"xmc2010v@163.com",
            attachfiles
    )

if __name__ == "__main__":
    #schedule.every(1).days.do(job)
    schedule.every().day.at("20:00").do(job)

    while 1:
        schedule.run_pending()
        time.sleep(5)

    for c in companys:
        gdbs[c].close()
