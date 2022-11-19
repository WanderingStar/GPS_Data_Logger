#!/usr/bin/bash

D=$(date +%Y-%m-%d)
/home/pi/GPS_Data_Logger/export.py -p $D /home/pi/Tracks/$D-big.gpx
gpsbabel -i gpx -f /home/pi/Tracks/$D-big.gpx \
    -x discard,hdop=10,vdop=20 \
    -x simplify,count=1440 \
    -o gpx -F /home/pi/Tracks/$D.gpx