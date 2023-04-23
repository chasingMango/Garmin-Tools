from garminconnect import Garmin
import os
import sys
import json
import zipfile
import configparser
import subprocess

from common import *

DOWNLOAD_ORIGINAL = Garmin.ActivityDownloadFormat.ORIGINAL
DOWNLOAD_TCX = Garmin.ActivityDownloadFormat.TCX

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
json_folder = os.path.join(activity_folder,"json-metadata")
fit_json_folder = os.path.join(activity_folder,"fit-to-json")
fit_tcx_folder = os.path.join(activity_folder,"fit-to-tcx")

#make the folders if they don't already exist
for p in {activity_folder,json_folder,fit_json_folder,fit_tcx_folder}:
    if not os.path.exists(p):
        os.makedirs(p)

# get user input for actions to perform

print("------------------------")
print("Weclome to Garmin Tools!")
print("------------------------\n")

if TESTING:
    download_all_activies = False
    save_json_metadata = True
    convert_fit_to_json = False
    download_TCX_version_for_FIT = False
    overwrite_if_exists = False
else:
    download_all_activies = get_yes_no("Download all activities?")
    save_json_metadata = get_yes_no("Download activity's json metadata (put in "+json_folder+")?")
    convert_fit_to_json = get_yes_no("Auto-convert downloaded FIT files to JSON (put in "+fit_json_folder+")?")
    download_TCX_version_for_FIT = get_yes_no("Download TCX version for FIT files (put in "+fit_tcx_folder+")")
    overwrite_if_exists = get_yes_no("Overwrite files that have already been downloaded?")

# log into Garmin Connect
gc = Garmin(email=email, password=password)
print("Logging in...")
if gc.login() == False:
    print("Failed to log in to Garmin Connect.")
    sys.exit()
print ("Logged in.")

#start the download process...
for i in range(9999999):

    try:
        #get the next activity form Garmin Connect
        activity=gc.get_activities(i,1)[0]
    except:
        #if there is an error, then all activities have been parsed; break out of for loop
        break

    activityId = activity["activityId"]
    activityName = activity["activityName"]
    activityDateTime = activity["startTimeLocal"][:10]
    print("Found activity", i,activityId,activityName,activityDateTime)

    # formulate activity name into a string that can be used in a filename
    # this could probalby be prettier...
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
    if save_json_metadata and ((not activity_file_exists(json_folder,activityId)) or overwrite_if_exists):
        print("---> Saved JSON metadata")
        filename = json_folder + "/" + filename_body + ".json"
        with open(filename, 'w') as f:
            json.dump(activity, f, ensure_ascii=False)
        edit_file_modified(filename, get_DateTime_from_string(activity["startTimeLocal"]))

    # check if the activity has already been downloaded by looking for a file with the activityId in the filename
    if download_all_activies and ((not activity_file_exists(activity_folder,activityId)) or overwrite_if_exists):
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
    if download_all_activies and (filename[-3:]=="fit" and download_TCX_version_for_FIT and (not activity_file_exists(fit_tcx_folder,activityId))):
        print("---> Downloading TCX version")
        download = gc.download_activity(activityId,DOWNLOAD_TCX)
        TCX_filename = fit_tcx_folder + "/" + filename_body + ".tcx"
        file = open(TCX_filename, 'wb')
        file.write(download)
        file.close()

    # if a FIT file was just downloaded, convert it to a separate JSON file too
    if convert_fit_to_json and filename[-3:]=="fit":
        print("---> Converting FIT to JSON")
        converted_filename = fit_json_folder + "/" + os.path.basename(filename)[:-3] + "json"
        cmd_str = "fitjson --pretty -o \"" + converted_filename + "\" \"" + filename + "\""
        subprocess.run(cmd_str, shell=True)
        time = os.path.getmtime(filename)
        os.utime(converted_filename, (time,time))

print("All done!")