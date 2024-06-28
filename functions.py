import stravalib
import pandas as pd
import folium
import random
import pathlib


def getStream(_client, _type_list, _activity_id):
    _activity_stream = _client.get_activity_streams(_activity_id,
                                                    types=_type_list,
                                                    resolution='medium',
                                                    series_type='distance')
    print(_activity_stream)
    return _activity_stream


def storeStream(_type_list, _activity_stream):
    df = pd.DataFrame()
    if _activity_stream is not None:
        for item in _type_list:
            if item in _activity_stream.keys():
                df[item] = pd.Series(_activity_stream[item].data, index=None)
    return df


def makePolyLine(df):
    lat_long_list = []
    for x in df['latlng']:
        lat_long_list.append(tuple(x))
    return lat_long_list


def plotMap(activityPolyLine, num, distanceList):
    print(activityPolyLine)
    activityMap = folium.Map(location=[activityPolyLine[0][0][0], activityPolyLine[0][0][1]], zoom_start=14,
                             width='100%') #, tiles='Stamen Terrain', attr='Stamen Terrain')
    folium.TileLayer('cartodbpositron').add_to(activityMap)
    folium.TileLayer('cartodbdark_matter').add_to(activityMap)

    # There's something up with this tile layer.
    # folium.TileLayer('Stamen Toner').add_to(activityMap)
    basePath = pathlib.Path(__file__).parent

    if len(activityPolyLine) == 1:
        folium.PolyLine(activityPolyLine).add_to(activityMap)
        mapPath = str(basePath) + "example" + str(num) + ".html"
        activityMap.save(mapPath)
    else:
        baseColor = "#FF0000"
        counter = 1
        for poly in activityPolyLine:
            folium.PolyLine(poly, color=baseColor).add_to(activityMap)
            baseColor = "#" + "%06x" % random.randint(0, 0x888888)
            counter += 1

        folium.LayerControl(collapsed=False).add_to(activityMap)

        mapPath = str(basePath) + "example" + str(num) + ".html"
        activityMap.save(mapPath)
        activityMap.save('example' + str(num) + '.html')
    return activityMap
