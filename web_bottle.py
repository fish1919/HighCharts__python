#!/usr/bin/python2
#
# 06.11.2016  Copyright (C) by meigrafd (meiraspi@gmail.com) published under the MIT License
#
# NOTE:
# Im using CyMySQL which is a fork of pymysql with speedups. See http://stackoverflow.com/a/25724855
#
#
from __future__ import print_function
from collections import OrderedDict
import os.path
import bottle
import json
import sys
import time
import cymysql

#------------------------------------------------------------------------

mysqlHost = '127.0.0.1'
mysqlPort = 3306
mysqlLogin = 'root'
mysqlPass = 'raspberrypi'
mysqlDatabase = 'measurements'

#------------------------------------------------------------------------

chart=OrderedDict()
chart['30mi'] = 'of the last 30 minutes'
chart['1h'] = 'of the last 1 hour'
chart['2h'] = 'of the last 2 hours'
chart['3h'] = 'of the last 3 hours'
chart['6h'] = 'of the last 6 hours'
chart['12h'] = 'of the last 12 hours'
chart['24h'] = 'of the last 24 hours'
chart['2d'] = 'of the last 2 days'
chart['3d'] = 'of the last 3 days'
chart['1w'] = 'of the last week'
chart['2w'] = 'of the last 2 weeks'
chart['1m'] = 'of the last month'
chart['3m'] = 'of the last 3 months'
chart['6m'] = 'of the last 6 months'
chart['1y'] = 'of the last year'

setting=dict()
setting['page_title'] = 'Sensor Infos via HighCharts and bottle'
setting['default_chart'] = chart.keys()[-1]    # in this case: 1y
setting['DEBUG'] = False

#------------------------------------------------------------------------


class DB(object):
    def __init__(self, host, port, user, passwd, db):
        self.conn = None
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.db = db
        self.debug = False
    
    def connect(self):
        try:
            self.conn = cymysql.connect(host=self.host, port=self.port, user=self.user, passwd=self.passwd, db=self.db)
        except Exception, err:
            print("MySQL Error: "+str(err[1]))
            self._close()
            sys.exit()
    
    def _close(self):
        try: self.cursor.close()
        except: pass
        try: self.conn.close()
        except: pass
    
    def query(self, sql):
        if self.debug: print("SQL: {}".format(sql))
        try:
            self.cursor = self.conn.cursor()
            self.cursor.execute(sql)
            self.conn.commit()
        except (AttributeError, cymysql.OperationalError):
            self.connect()
            self.cursor = self.conn.cursor()
            self.cursor.execute(sql)
            self.conn.commit()


def printD(message):
    if setting['DEBUG']:
        print(message)


def get_SQL_Period_Unit(period):
    switcher = {
        's': "SECOND",
        'mi': "MINUTE",
        'h': "HOUR",
        'd': "DAY",
        'w': "WEEK",
        'm': "MONTH",
        'y': "YEAR",
    }
    return switcher.get(period)


# ----------------------------------------------------
# Bottle Routes
# ----------------------------------------------------

@bottle.route('/')
def IndexHandler():
    setting['period'] = bottle.request.query.period or setting['default_chart']
    # remove all numbers from period string (eg. from 12h so only h is left)
    setting['periot_unit'] = ''.join([i for i in setting['period'] if not i.isdigit()])
    # remove the Unit from period string so only numbers are left
    setting['periot_num'] = ''.join([i for i in setting['period'] if i.isdigit()])
    printD("Period: {}".format(setting['period']))
    
    values = {
        'chart': chart,
        'debug': setting['DEBUG'],
        'Period': setting['period'],
        'setting': setting,
    }
    return bottle.template('index.html', values)


@bottle.route('/data')
def DataHandler():
    setting['type'] = bottle.request.query.type or 'temp'
    printD("Data Request: {}".format(setting['type']))
    
    # Get timestamp from last database entry
    db.query("SELECT timestamp,{} FROM data WHERE 1 ORDER BY timestamp DESC LIMIT 0,1" . format(setting['type']))
    lastTimestamp = db.cursor.fetchone()[0]
    if not lastTimestamp:
        lastTimestamp = time.time()
    
    # Get each "location"
    db.query("SELECT location FROM data GROUP BY location")
    
    # Get Data from each "location"
    db2 = DB(host=mysqlHost, port=mysqlPort, user=mysqlLogin, passwd=mysqlPass, db=mysqlDatabase)
    #db2.debug=setting['DEBUG']
    dataResult=list()
    for row in db.cursor.fetchall():
        location = row[0]
        printD("fetching data of location: {}".format(location))
        db2.query("SELECT location,timestamp,{0} FROM data WHERE location='{1}' AND timestamp >= UNIX_TIMESTAMP(DATE_SUB(FROM_UNIXTIME({2}), INTERVAL {3} {4})) AND timestamp <= UNIX_TIMESTAMP() ORDER BY timestamp ASC;" . format(setting['type'],location,lastTimestamp,setting['periot_num'],get_SQL_Period_Unit(setting['periot_unit'])) )
        results=dict()
        results['data']=list()
        for row2 in db2.cursor.fetchall():
            loc = row2[0]
            ts = row2[1]
            val = row2[2]
            if val:
                printD("loc: {}, ts: {}, val: {}".format(loc, ts , val))
                # Convert 'ts' from Unix timestamp to JavaScript time
                ts = float(ts*1000)
                results['data'].append([ ts , val ])
        
        printD("Results: {}".format(len(results['data'])))
        if len(results['data']):
            results['name'] = location
            dataResult.append(results)
    
    db2._close()
    if len(dataResult):
        bottle.response.content_type = 'application/json'
        return json.dumps(dataResult)    
    else:
        return


@bottle.route('/static/<filename:path>')
def StaticHandler(filename):
    if filename.endswith(".css"):
        bottle.response.content_type = 'text/css'
    elif filename.endswith(".js"):
        bottle.response.content_type = 'text/javascript'
    elif filename.endswith(".png"):
        bottle.response.content_type = 'image/png'   
    return bottle.static_file(filename, root=os.path.join(os.path.dirname(__file__), 'static'))


@bottle.error(404)
def error404(error):
    return 'Error 404: Nothing here, sorry.'


try:
    db = DB(host=mysqlHost, port=mysqlPort, user=mysqlLogin, passwd=mysqlPass, db=mysqlDatabase)
    db.query("CREATE DATABASE IF NOT EXISTS %s;" % mysqlDatabase)
    db.query("USE %s;" % mysqlDatabase)
    db.query("CREATE TABLE IF NOT EXISTS data \
             (id INT(11) UNSIGNED AUTO_INCREMENT PRIMARY KEY,location VARCHAR(255),timestamp INT(11),temp FLOAT(11),hum FLOAT(11),KEY location (location)) \
             ENGINE=InnoDB DEFAULT CHARSET=utf8;"
            )
    setting['period'] = None
    setting['type'] = None
    
    bottle.TEMPLATE_PATH.insert(0, os.path.join(os.path.dirname(__file__), 'templates'))
    bottle.run(host='0.0.0.0', port=80, quiet=True, debug=bool(setting['DEBUG']))
except (KeyboardInterrupt, SystemExit):
    if db: db._close()
    print('\nQuit\n')

#EOF