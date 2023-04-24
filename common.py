import datetime
import time
import os
import glob
import json

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

def get_activity_filename(path, activityId):
    activity_matches = glob.glob(path + "/*(" + str(activityId) + ")*")
    count =  len(activity_matches)
    if count==1:
        return activity_matches[0]
    else:
        return None

def activity_file_exists(path, activityId):
    return get_activity_filename(path,activityId) is not None

def activity_file_does_not_exist(path, activityID):
    return not activity_file_exists(path,activityID)

def fit_activity_file_exists(path,activityID):
    return len(glob.glob(path + "/*(" + str(activityID) + ")*.fit")) > 0

def get_most_recent_activity_metadata(json_metadata_folder):
    most_recent_starttime = None
    most_recent_metadata = None
    for metadata_filename in glob.glob(json_metadata_folder + "/*.json"):
        f = open(metadata_filename, 'r')
        #print(metadata_filename)
        try:
            metadata = json.loads(f.read())
            startTimeLocal = metadata["startTimeLocal"]
        except:
            startTimeLocal = None
        f.close()
        startTimeLocal=metadata["startTimeLocal"]
        if most_recent_starttime is None or startTimeLocal>most_recent_starttime:
            most_recent_starttime = startTimeLocal
            most_recent_metadata = metadata
    return most_recent_metadata

def get_most_recent_activity_startTime(json_metadata_folder):
    return get_most_recent_activity_metadata(json_metadata_folder)["startTimeLocal"]

def get_activity_start_datetime(activity):
    return datetime.datetime.strptime(activity["startTimeLocal"],'%Y-%m-%d %H:%M:%S')