import datetime
import time
import os
import glob

def get_yes_no(prompt=None, repeat_until_valid_response=True):
    default_prompt = "(y)es/(n)o: "

    while True:
        if prompt is not None:
            s=input(prompt + " " + default_prompt)
        else:
            s=input(default_prompt)
        if str.lower(s) in {"yes","y"}:
            return True
        elif str.lower(s) in {"no","n"}:
            return False
        elif not repeat_until_valid_response:
            return None

def get_DateTime_from_string(s):
    year = int(s[:4])
    month = int(s[5:7])
    day = int(s[8:10])
    hour = int(s[11:13])
    minute = int(s[14:16])
    second = int(s[17:19])
    return datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)

def edit_file_modified(filename,date):
    modTime = time.mktime(date.timetuple())
    os.utime(filename, (modTime, modTime))

def activity_file_exists(path, activityID):
    return len(glob.glob(path + "*(" + str(activityID) + ")*"))>0