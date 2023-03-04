#!/usr/bin/python3

from datetime import datetime, timezone
import re
import mechanicalsoup
import os

from config import config
from core import database, export
from helpers import logger

# Initialize the logger
logger = logger.get_logger('gps_exporter')

if __name__ == '__main__':
    where = "utc_time IS NOT NULL ORDER BY utc_time DESC LIMIT 1"

    # Initialization
    config_file = os.path.dirname(__file__) + "/config/config.json"

    # Read the application config
    appConfig = config.AppConfig(config_file)
    rc = appConfig.load_app_config()

    try:
        # attempt to connect to database (create database if does not already exist)
        connection_handler = database.connect(db_filename=appConfig.database_filename)
        # if no connection handler, then give up
        if connection_handler is not None:
            data = database.retrieve_data_where(connection_handler, where)
            if data[0]:
                lat = round(data[0].latitude, ndigits=4)
                lon = round(data[0].longitude, ndigits=4)
                browser = mechanicalsoup.StatefulBrowser(user_agent='MechanicalSoup')
                # yes, yes, shouldn't check this bit in
                response = browser.open("http://localhost/views.php?view=Settings", auth=("birdnet", ""))
                if not response.ok:
                    print(f"Got {response.status_code} from {browser.get_url()}")
                    exit(1)
                form = browser.select_form("#basicform")
                form["latitude"] = lat
                form["longitude"] = lon
                form["date"] = None
                form["time"] = None
                response = browser.submit_selected(auth=("birdnet", ""))
                if not response.ok:
                    print(f"Got {response.status_code} from {browser.get_url()}")
                    exit(1)
        with open('/home/pi/birdnet_gps.log', 'a') as f:
            print(f"Set lat, lon to ({lat}, {lon})", file=f)

    except Exception as error:
        logger.error(f"Exception: {str(error)}")

