from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
import os
import sys
import json
import zipfile
import configparser
import subprocess
from datetime import datetime as dt, timedelta
import requests

from common import *

DOWNLOAD_ORIGINAL = Garmin.ActivityDownloadFormat.ORIGINAL
DOWNLOAD_TCX = Garmin.ActivityDownloadFormat.TCX

TESTING = False

settings_filename = "settings.ini"

def process_activity(activity):
    activityId = activity["activityId"]
    activityName = activity["activityName"]
    activityDateTime = activity["startTimeLocal"][:10]

    # formulate activity name into a string that can be used in a filename
    # this could probably be prettier...
    if activityName == "None":
        activityName = "Untitled"
    else:
        try:
            activityName = activityName.replace("/", "_")
        except:
            pass
        try:
            activityName = activityName.replace(">", "")
        except:
            pass

    # filename body that will be used for all other files
    filename_body = "%s %s (%s)" % (activityDateTime, activityName, activityId)

    # save activity's json meta-data
    if save_json_metadata and (overwrite_if_exists or activity_file_does_not_exist(metadata_folder,activityId)):
        print("---> Saved JSON metadata")
        filename = metadata_folder + "/" + filename_body + ".json"
        with open(filename, 'w') as f:
            json.dump(activity, f, ensure_ascii=False)
        edit_file_modified(filename, get_DateTime_from_string(activity["startTimeLocal"]))

    # check if the activity has already been downloaded by looking for a file with the activityId in the filename
    if (not activity_file_exists(activity_folder,activityId)) or overwrite_if_exists:
        print("---> Downloading activity file")

        # try downloading the file in the orginal format.  if there is an error then the activity
        # has no original file to download, can be exported via TCX
        try:
            download = gc.download_activity(activityId,DOWNLOAD_ORIGINAL)
            download_format = DOWNLOAD_ORIGINAL
            filename = activity_folder + "/" + filename_body + ".zip"
        except:
            download = gc.download_activity(activityId, DOWNLOAD_TCX)
            download_format = DOWNLOAD_TCX
            filename = activity_folder + "/" + filename_body+".tcx"

        #write the activity to a file
        file = open(filename, 'wb')
        file.write(download)
        file.close()

        # auto-extract file from zip file if it was downloaded as original (Garmin stores
        # the FIT files as zips
        if download_format==DOWNLOAD_ORIGINAL:
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                zip_ref.extractall(activity_folder)
                extracted_filename = activity_folder + "/" + zip_ref.namelist()[0]
            os.remove(filename)
            filename = activity_folder + "/" + filename_body + "." + extracted_filename[-3:]
            os.rename(extracted_filename, filename)

        # change the file's "modified" date and time to match that of the activity start
        edit_file_modified(filename,get_DateTime_from_string(activity["startTimeLocal"]))

    elif activity_file_exists(activity_folder,activityId):
        print("---> Activity file already downloaded")

    # if a FIT file was just downloaded, download the TCX version too
    if download_TCX_version_for_FIT and fit_activity_file_exists(activity_folder,activityId) and (overwrite_if_exists or activity_file_does_not_exist(fit_tcx_folder,activityId)):
        print("---> Downloading TCX version")
        download = gc.download_activity(activityId,DOWNLOAD_TCX)
        TCX_filename = fit_tcx_folder + "/" + filename_body + ".tcx"
        file = open(TCX_filename, 'wb')
        file.write(download)
        file.close()
        edit_file_modified(TCX_filename, get_DateTime_from_string(activity["startTimeLocal"]))

    # if a FIT file was just downloaded, convert it to a separate JSON file too
    if convert_fit_to_json and fit_activity_file_exists(activity_folder,activityId) and (overwrite_if_exists or activity_file_does_not_exist(fit_json_folder,activityId)):
        print("---> Converting FIT to JSON")
        fit_filename = get_activity_filename(activity_folder,activityId)
        converted_filename = fit_json_folder + "/" + os.path.basename(fit_filename[:-3]) + "json"
        cmd_str = "fitjson --pretty -o \"" + converted_filename + "\" \"" + fit_filename + "\""
        subprocess.run(cmd_str, shell=True)
        edit_file_modified(converted_filename, dt.fromtimestamp(os.path.getmtime(fit_filename)))

#This function is borrowed from the example program from garminconnect: https://pypi.org/project/garminconnect/
def init_api(email, password):
    """Initialize Garmin API with your credentials."""

    try:
        ## Try to load the previous session
        with open("session.json") as f:
            saved_session = json.load(f)
            print(
                "Logging in to Garmin Connect using session loaded from 'session.json'..."
            )

            # Use the loaded session for initializing the API (without need for credentials)
            api = Garmin(session_data=saved_session)

            # Login using the
            api.login()

    except (FileNotFoundError, GarminConnectAuthenticationError):
        # Login to Garmin Connect portal with credentials since session is invalid or not present.
        print(
            "Session file not present or turned invalid, login with your Garmin Connect credentials.\n"
            "NOTE: Credentials will not be stored, the session cookies will be stored in 'session.json' for future use.\n"
        )
        try:
            api = Garmin(email, password)
            api.login()

            # Save session dictionary to json file for future use
            with open("session.json", "w", encoding="utf-8") as f:
                json.dump(api.session_data, f, ensure_ascii=False, indent=4)
        except (
            GarminConnectConnectionError,
            GarminConnectAuthenticationError,
            GarminConnectTooManyRequestsError,
            requests.exceptions.HTTPError,
        ) as err:
            logger.error("Error occurred during Garmin Connect communication: %s", err)
            return None
    return api

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
metadata_folder = os.path.join(activity_folder,"json-metadata")
fit_json_folder = os.path.join(activity_folder,"fit-to-json")
fit_tcx_folder = os.path.join(activity_folder,"fit-to-tcx")

#make the folders if they don't already exist
for p in {activity_folder,metadata_folder,fit_json_folder,fit_tcx_folder}:
    if not os.path.exists(p):
        os.makedirs(p)

# get user input for actions to perform

print("------------------------")
print("Weclome to OPSEC Fitness!")
print("------------------------\n")

if TESTING:
    download_all_activities = True
    download_new_activities = True
    save_json_metadata = True
    convert_fit_to_json = True
    download_TCX_version_for_FIT = True
    overwrite_if_exists = False
else:
    download_all_activities = get_yes_no("Download all activities?")
    if not download_all_activities:
        download_new_activities = get_yes_no("Download new activities?")
    save_json_metadata = get_yes_no("Download activity's json metadata (put in "+metadata_folder+")?")
    convert_fit_to_json = get_yes_no("Auto-convert downloaded FIT files to JSON (put in "+fit_json_folder+")?")
    download_TCX_version_for_FIT = get_yes_no("Download TCX version for FIT files (put in "+fit_tcx_folder+")")
    overwrite_if_exists = get_yes_no("Overwrite files that have already been downloaded?")

# log into Garmin Connect-------------
print("Logging in...")
#this will use the saved session token if available, otherwise log in with
#username and password, then save the session token to session.json
gc = init_api(email,password)
if gc == False:
    print("Failed to log in to Garmin Connect.")
    sys.exit()
print ("Logged in.")
#-------------------------------------


#start the download process...
if download_all_activities:
    for i in range(9999999):
        try:
            #get the next activity form Garmin Connect
            activity=gc.get_activities(i,1)[0]
        except:
            #if there is an error, then all activities have been parsed; break out of for loop
            break
        print("Found activity", i, activity["activityId"], activity["activityName"], activity["startTimeLocal"])
        process_activity(activity)
elif download_new_activities:
    most_recent_activity_time = dt.strptime(get_most_recent_activity_startTime(metadata_folder),'%Y-%m-%d %H:%M:%S')
    #start the search beginning from one minute after the most recent activity downloaded
    search_start_time = most_recent_activity_time + timedelta(minutes=1)
    new_activities = gc.get_activities_by_date(search_start_time,dt.now())
    i=0
    for activity in new_activities:
        if(get_activity_start_datetime(activity)>most_recent_activity_time):
            i+=1
            #subtract 1 from the length in the status message because the most recent activity is included in the count
            print("Found activity", i, "of",len(new_activities), activity["activityId"], activity["activityName"], activity["startTimeLocal"]-1)
            process_activity(activity)
    if i==0:
        print ("No new activities found.")

print("All done!")