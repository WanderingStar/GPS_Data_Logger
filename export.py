#!/usr/bin/env python3

import argparse
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import re

from config import config
from core import database, export
from helpers import logger

def complete(prefix):
    """
    The earliest complete timestamp that could be represented by the prefix
    """
    rest = '0000-00-00T00:00:00'
    merged = prefix + rest[len(prefix):]
    return merged.replace('-00', '-01')

def successor(prefix):
    """
    A value just after the supplied timestamp prefix
    """
    completed = complete(prefix)
    dt = datetime.fromisoformat(completed)
    if re.search(":\d\d:\d\d$", prefix):
        return dt + relativedelta(seconds=1)
    if re.search(":\d\d:\d$", prefix):
        return dt + relativedelta(seconds=10)
    if re.search(":\d\d$", prefix):
        return dt + relativedelta(minutes=1)
    if re.search(":\d$", prefix):
        return dt + relativedelta(minutes=10)
    if re.search("T\d\d$", prefix):
        return dt + relativedelta(hours=1)
    if re.search("T\d$", prefix):
        return dt + relativedelta(hours=10)
    if re.search("-\d\d-\d\d$", prefix):
        return dt + relativedelta(days=1)
    if re.search("-\d\d-\d$", prefix):
        return dt + relativedelta(days=10)
    if re.search("-\d\d$", prefix):
        return dt + relativedelta(months=1)
    if re.search("-0$", prefix):
        # kind of nonsensical
        return dt.replace(month=10)
    if re.search("-1$", prefix):
        # kind of nonsensical
        return datetime(year=dt.year + 1, month=1, day=1)
    if re.match("\d\d\d\d-?$"):
        return datetime(year=dt.year + 1, month=1, day=1)
    if re.match("\d\d\d$"):
        return datetime(year=dt.year + 10, month=1, day=1)
    if re.match("\d\d$"):
        return datetime(year=dt.year + 100, month=1, day=1)
    if re.match("\d$"):
        return datetime(year=dt.year + 1000, month=1, day=1)
    # Y10K bug
    return None

def where_local_time_between(start, end):
    start = complete(start)
    end = successor(end)

    utc_start = datetime.fromisoformat(start).astimezone(timezone.utc)
    utc_end = end.astimezone(timezone.utc)

    return f"utc_time >= '{utc_start.isoformat()}' AND utc_time < '{utc_end.isoformat()}'"


# Initialize the logger
logger = logger.get_logger('gps_exporter')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog = 'GPS data export',
        description = 'Exports data from the GPS database')
    parser.add_argument('output_filename')
    parser.add_argument('-s', '--start', help='export data with timestamps between this and end')
    parser.add_argument('-e', '--end', help='export data with timestamps between this and start')
    parser.add_argument('-p', '--prefix', help='export data with timestamps starting with this prefix eg. 2022-11- for a month')
    parser.add_argument('-l', '--last', type=int, help='export data from most recent N seconds')

    date_prefix = re.compile('^\d(\d(\d(\d(-(\d(\d(-(\d(\d(T(\d(\d(:(\d(\d(:(\d(\d)?)?)?)?)?)?)?)?)?)?)?)?)?)?)?)?)?)?$')
    args = parser.parse_args()

    output_filename = args.output_filename
    if output_filename.endswith('.gpx'):
        format = 'gpx'
    elif output_filename.endswith('.kml'):
        format = 'kml'
    else:
        print("Error: Output filename should be .gpx or .kml")
        exit(1)

    where = None
    if args.start is not None and args.end is not None:
        if args.prefix is not None or args.last is not None:
            print("Error: Provide only one of start/end, prefix, or last")
            exit(1)

        start = args.start
        end = args.end
        if not re.match(date_prefix, start):
            print("Error: Start must be a prefix of a timestamp in the format 2022-11-05T20:15:30, got: " + start)
            exit(1)
        if not re.match(date_prefix, end):
            print("Error: End must be a prefix of a timestamp in the format 2022-11-05T20:15:30, got: " + end)
            exit(1)

        where = where_local_time_between(start, end)
    elif args.prefix is not None:
        if args.last is not None or args.start is not None or args.end is not None:
            print("Error: Provide only one of start/end, prefix, or last")
            exit(1)
        
        prefix = args.prefix
        if not re.match(date_prefix, prefix):
            print("Error: prefix of a timestamp in the format 2022-11-05T20:15:30, got: " + prefix)
            exit(1)

        where = where_local_time_between(prefix, prefix)
    elif args.last is not None:
        print("Error: last is not implemented yet")
        exit(1)
    else:
        print("Error: Provide one of start/end, prefix, or last")
        exit(1)

    print(where)

    # Initialization
    config_file = "./config/config.json"

    # Read the application config
    appConfig = config.AppConfig(config_file)
    rc = appConfig.load_app_config()

    try:
        # attempt to connect to database (create database if does not already exist)
        connection_handler = database.connect(db_filename=appConfig.database_filename)
        # if no connection handler, then give up
        if connection_handler is not None:
            data = database.retrieve_data_where(connection_handler, where)
            print(f"Found {len(data)} locations")
            if format == 'gpx':
                export.save_as_gpx(output_filename, data)
            elif format == 'kml':
                export.save_as_kml(output_filename, data)
            database.disconnect(connection_handler)

    except Exception as error:
        logger.error(f"Exception: {str(error)}")

