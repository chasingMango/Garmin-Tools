from garmin_fit_sdk import Decoder, Stream
#import xml.etree.cElementTree as ET
import lxml.etree as ET

from os.path import exists

semicircle_conversion = 180/pow(2,31)

#Transposes the track exactly based on new starting latitude and longitude.
#Currently returns a list of transposed GPS coordinates, can't save FIT file yet.
def transpose_FIT(fit_stream, transposed_starting_lat, transposed_starting_lon):

    #if fit_stream is a string, check if it is a fit file and load a stream from that file
    if type(fit_stream=="str"):
        if exists(fit_stream):
            fit_stream = Stream.from_file(fit_stream)
        else:
            return None

    transposed_coords = []
    decoder = Decoder(fit_stream)
    messages, errors = decoder.read()
    delta_lat = None
    delta_lon = None

    for message in messages["record_mesgs"]:
        lat = message["position_lat"]*semicircle_conversion
        lon = message["position_long"]*semicircle_conversion
        alt = message["enhanced_altitude"]

        if delta_lat is None:
            delta_lat = lat - transposed_starting_lat
            delta_lon = lon - transposed_starting_lon

        transposed_lon = lon - delta_lon
        transposed_lat = lat - delta_lat
        transposed_coords.append([transposed_lon, transposed_lat, alt])

    return transposed_coords

def transpose_TCX(TCX_filename, transposed_starting_lat, transposed_starting_lon, save_file_overwrite=False,new_filename=None,return_format="xml"):

    #Use lxml to avoid writing namespaces to tags, which TCX does not do
    tree = ET.parse(TCX_filename)
    root = tree.getroot()

    transposed_coords = []
    delta_lat = None
    delta_lon = None

    for trackpoint in root.iter("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Trackpoint"):
        position = trackpoint.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Position')
        lat = float(position.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}LatitudeDegrees').text)
        lon = float(position.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}LongitudeDegrees').text)
        alt = float(trackpoint.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}AltitudeMeters').text)

        if delta_lat is None:
            delta_lat = lat - transposed_starting_lat
            delta_lon = lon - transposed_starting_lon

        transposed_lon = lon - delta_lon
        transposed_lat = lat - delta_lat
        position.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}LatitudeDegrees').text=str(transposed_lat)
        position.find('{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}LongitudeDegrees').text=str(transposed_lon)
        transposed_coords.append([transposed_lon, transposed_lat, alt])

    if save_file_overwrite:
        if new_filename is not None:
            tree.write(new_filename)
        else:
            tree.write(TCX_filename)

    if return_format=="list":
        return transposed_coords
    else:
        return tree