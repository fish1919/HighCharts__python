Using Python Bottle with MySQL and HighCharts to display Sensor Data

See also the Main Project: https://github.com/meigrafd/HighCharts
****************************************************


Installation:
--------

```
sudo apt-get install git-core python-pip
sudo pip install bottle cymysql
git clone https://github.com/meigrafd/HighCharts__python .
```

Edit web_bottle.py and configure the mysql lines:
```
mysqlHost = '127.0.0.1'
mysqlPort = 3306
mysqlLogin = 'root'
mysqlPass = 'raspberrypi'
mysqlDatabase = 'measurements'
```

Run web_bottle.py and surf to your Server's IP...
```
python web_bottle.py
```



****************************************************
Project Thread: https://forum-raspberrypi.de/forum/thread/30049-python-mysql-webserver-veranschaulichung-mit-graphen/?postID=248721#post248721

