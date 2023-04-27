from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
import os
import sys
import json
import configparser
import backup

import requests

from common import *

TESTING = False

settings_filename = "settings.ini"

#if there is no settings file, get user input and create settings file
config=configparser.ConfigParser()
if not os.path.isfile(settings_filename):
    config['Login'] = {"email":input("Email: "),
                       "password":input("Password: ")}
    config['Folders'] = {"activity_folder":input("Activity folder location: ")}

#load settings from settings file
config.read(settings_filename)
email = config["Login"]["email"]
password = config["Login"]["password"]
activity_folder = config["Folders"]["activity_folder"]

# get user input for actions to perform

print("------------------------")
print("Weclome to OPSEC Fitness!")
print("------------------------\n")

metadata_folder =  backup.get_metadata_folder(activity_folder)
fit_json_folder = backup.get_json_folder(activity_folder)
fit_tcx_folder = backup.get_tcx_folder(activity_folder)

download_all_activities = get_yes_no("Download all activities?")
if not download_all_activities:
    try:
        print("Most recent activity is from " + str(get_most_recent_activity_startTime(metadata_folder)) + ".  Newer activities will be downloaded.")
    except:
        pass
save_json_metadata = get_yes_no("Save activity's json metadata (put in "+metadata_folder+")?")
download_TCX_version_for_FIT = get_yes_no("For FIT files, also TCX version (put in "+fit_tcx_folder+")")
convert_fit_to_json = get_yes_no("For FIT files, auto-convert a JSON version (put in "+fit_json_folder+")?")
overwrite_if_exists = get_yes_no("Overwrite files that have already been downloaded?")

backup.backup_garmin_connect(email,password,download_all_activities=download_all_activities,save_json_metadata=save_json_metadata,download_TCX_version_for_FIT=download_TCX_version_for_FIT,convert_fit_to_json=convert_fit_to_json, overwrite_if_exists=overwrite_if_exists,activity_folder=activity_folder)

print("All done!")