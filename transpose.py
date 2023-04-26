from garmin_fit_sdk import Decoder, Stream

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
    starting_lat = None
    starting_lon = None

    for message in messages["record_mesgs"]:
        lat = message["position_lat"]*semicircle_conversion
        lon = message["position_long"]*semicircle_conversion
        alt = message["enhanced_altitude"]

        if starting_lat is None:
            starting_lat = lat
            starting_lon = lon

        transposed_lon = (lon-starting_lon)+transposed_starting_lon
        transposed_lat = (lat-starting_lat)+transposed_starting_lat
        transposed_coords.append([transposed_lon, transposed_lat, alt])

    return transposed_coords