from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from datetime import datetime as dt, timedelta
import subprocess
import requests
import zipfile

from common import *

metadata_path = "json-metadata"
fit_json_path = "fit-to-json"
fit_tcx_path = "fit-to-tcx"

def get_metadata_folder(activity_folder):
    return os.path.join(activity_folder, metadata_path)

def get_json_folder(activity_folder):
    return os.path.join(activity_folder, fit_json_path)

def get_tcx_folder(activity_folder):
    return os.path.join(activity_folder, fit_tcx_path)


def backup_garmin_connect(email=None,password=None,download_all_activities=True, save_json_metadata=True,overwrite_if_exists=False,download_TCX_version_for_FIT=False,convert_fit_to_json=False, activity_folder="./activities"):

    # log into Garmin Connect-------------
    print("Logging in...")
    # this will use the saved session token if available, otherwise log in with
    # username and password, then save the session token to session.json
    gc = __init_garmin_api(email, password)
    if gc == False:
        print("Failed to log in to Garmin Connect.")
        return None
    print("Logged in.")
    # -------------------------------------

    metadata_folder = os.path.join(activity_folder, metadata_path)

    # start the download process...
    if download_all_activities:
        print("Downloading all activities...")
        for i in range(9999999):
            try:
                # get the next activity form Garmin Connect
                activity = gc.get_activities(i, 1)[0]
            except:
                # if there is an error, then all activities have been parsed; break out of for loop
                break
            print("Found activity", i, activity["activityId"], activity["activityName"], activity["startTimeLocal"])
            __process_garmin_activity(garmin_connect_api=gc,activity=activity,save_json_metadata=save_json_metadata,overwrite_if_exists=overwrite_if_exists,download_TCX_version_for_FIT=download_TCX_version_for_FIT,convert_fit_to_json=convert_fit_to_json,activity_folder=activity_folder)
    #if download_all_activities is False, then only downloaed new activities
    #activities with timestamps after the most recent activity already downloaded
    else:
        most_recent_activity_time = dt.strptime(get_most_recent_activity_startTime(metadata_folder),
                                                '%Y-%m-%d %H:%M:%S')
        # start the search beginning from one minute after the most recent activity downloaded
        search_start_time = most_recent_activity_time + timedelta(minutes=1)
        new_activities = gc.get_activities_by_date(search_start_time, dt.now())
        i = 0
        for activity in new_activities:
            print(get_activity_start_datetime(activity))
            if (get_activity_start_datetime(activity) > most_recent_activity_time):
                i += 1
                # subtract 1 from the length in the status message because the most recent activity is included in the count
                print("Found activity", i, "of", len(new_activities), activity["activityId"], activity["activityName"],
                      activity["startTimeLocal"] - 1)
                __process_garmin_activity(garmin_connect_api=gc,activity=activity,save_json_metadata=save_json_metadata,overwrite_if_exists=overwrite_if_exists,download_TCX_version_for_FIT=download_TCX_version_for_FIT,convert_fit_to_json=convert_fit_to_json,activity_folder=activity_folder)
        if i == 0:
            print("No new activities found.")

# This function is borrowed from the example program from garminconnect: https://pypi.org/project/garminconnect/
def __init_garmin_api(email, password):
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


def __process_garmin_activity(garmin_connect_api, activity, save_json_metadata=True,overwrite_if_exists=False,download_TCX_version_for_FIT=False,convert_fit_to_json=False, activity_folder="./activities"):

    metadata_folder = os.path.join(activity_folder, metadata_path)
    fit_json_folder = os.path.join(activity_folder, fit_json_path)
    fit_tcx_folder = os.path.join(activity_folder, fit_tcx_path)

    # make the folders if they don't already exist
    for p in {activity_folder, metadata_folder, fit_json_folder, fit_tcx_folder}:
        if not os.path.exists(p):
            os.makedirs(p)

    activityId = activity["activityId"]
    activityName = activity["activityName"]
    activityDateTime = activity["startTimeLocal"][:10]

    DOWNLOAD_ORIGINAL = Garmin.ActivityDownloadFormat.ORIGINAL
    DOWNLOAD_TCX = Garmin.ActivityDownloadFormat.TCX

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

        # try downloading the file in the original format.  if there is an error then the activity
        # has no original file to download, can be exported via TCX
        try:
            download = garmin_connect_api.download_activity(activityId,DOWNLOAD_ORIGINAL)
            download_format = DOWNLOAD_ORIGINAL
            filename = activity_folder + "/" + filename_body + ".zip"
        except:
            download = garmin_connect_api.download_activity(activityId, DOWNLOAD_TCX)
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
        download = garmin_connect_api.download_activity(activityId,DOWNLOAD_TCX)
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


