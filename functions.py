import pandas as pd
import folium
import random
import math

import constants as const


def getStream(_client, _fetch_data_types, _activity_id, _activity_type='Run'):
    _activity_stream = _client.get_activity_streams(_activity_id,
                                                    types=_fetch_data_types,
                                                    resolution='medium',
                                                    series_type='distance')
    return _activity_stream


def storeStream(_type_list, _activity_stream) -> pd.DataFrame:
    df = pd.DataFrame()
    if _activity_stream is not None:
        for item in _type_list:
            if item in _activity_stream.keys():
                df[item] = pd.Series(_activity_stream[item].data, index=None)
    return df


def makePolyLine(df) -> list:
    lat_long_list = []
    for x in df['latlng']:
        lat_long_list.append(tuple(x))
    return lat_long_list


def plotMap(_activity_polyline):
    activityMap = folium.Map(location=[_activity_polyline[0][0][0], _activity_polyline[0][0][1]], zoom_start=14,
                             width='100%')
    folium.TileLayer('cartodbpositron').add_to(activityMap)
    folium.TileLayer('cartodbdark_matter').add_to(activityMap)

    if len(_activity_polyline) == 1:
        folium.PolyLine(_activity_polyline).add_to(activityMap)
    else:
        baseColor = "#FF0000"
        counter = 1
        for poly in _activity_polyline:
            folium.PolyLine(poly, color=baseColor).add_to(activityMap)
            baseColor = "#" + "%06x" % random.randint(0, 0x888888)
            counter += 1
        folium.LayerControl(collapsed=False).add_to(activityMap)

    return activityMap


def latlngDistance(_latlng_origin: tuple, _latlng_destination: tuple) -> float:
    # Tuple format should be (latitude, longitude)
    _lat1 = math.radians(_latlng_origin[0])
    _lat2 = math.radians(_latlng_destination[0])
    _long1 = math.radians(_latlng_origin[1])
    _long2 = math.radians(_latlng_destination[1])

    _delta_lat = _lat2 - _lat1
    _delta_long = _long2 - _long1

    _A = (math.sin(_delta_lat / 2) * math.sin(_delta_lat / 2) +
          math.sin(_delta_long / 2) * math.sin(_delta_long / 2) *
          math.cos(_lat1) * math.cos(_lat2))
    _distance = 2 * const.EARTH_RADIUS * math.asin(math.sqrt(_A))

    return _distance
