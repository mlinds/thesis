# This is adapted from a notebook on the nasa website, and is intended to be run interactively. Therefore there is a lot of extra code to handle the inputs
# from https://raw.githubusercontent.com/nsidc/NSIDC-Data-Access-Notebook/master/notebooks/Customize%20and%20Access%20NSIDC%20Data.ipynb
# it might be difficult to understand and debug, just be warned

# TODO change the blank strings thing to use kwargs

# %%
from gzip import READ
from mercantile import bounding_tile
import requests
import json
import zipfile
import io
import math
import os
import shutil
import pprint
import re
import time
import pandas as pd
from pandas import MultiIndex, Int16Dtype
import geopandas as gpd
import fiona
import matplotlib.pyplot as plt
from statistics import mean
from shapely.geometry.polygon import orient
from atl_module.secret_vars import EARTHDATA_PASSWORD, EARTHDATA_USERNAME, EMAIL
from atl_module.io.variablelist import atl_03_vars, segment_vars, atl09_vars
from xml.etree import ElementTree as ET

# To read KML files with geopandas, we will need to enable KML support in fiona (disabled by default)
fiona.drvsupport.supported_drivers["LIBKML"] = "rw"

BASE_URL = "https://n5eil02u.ecs.nsidc.org/egi/request"
CMR_COLLECTIONS_URL = "https://cmr.earthdata.nasa.gov/search/collections.json"
GRANULE_SEARCH_URL = "https://cmr.earthdata.nasa.gov/search/granules"


def _get_product_metadata(product_short_name):
    response = requests.get(
        CMR_COLLECTIONS_URL, params={"short_name": product_short_name}
    )
    results = json.loads(response.content)
    print(results)

    # Find all instances of 'version_id' in metadata and print most recent version number
    versions = [el["version_id"] for el in results["feed"]["entry"]]
    latest_version = versions[-1]
    return latest_version


def _prepare_geo_file(bounds_filepath):
    # Use geopandas to read in polygon file
    # Note: a KML or geojson, or almost any other vector-based spatial data format could be substituted here.

    # Go from geopandas GeoDataFrame object to an input that is readable by CMR
    gdf = gpd.read_file(bounds_filepath)
    # gdf.to_crs(epsg=4326,inplace=True)

    # CMR polygon points need to be provided in counter-clockwise order. The last point should match the first point to close the polygon.

    # Simplify polygon for complex shapes in order to pass a reasonable request length to CMR. The larger the tolerance value, the more simplified the polygon.
    # Orient counter-clockwise: CMR polygon points need to be provided in counter-clockwise order. The last point should match the first point to close the polygon.
    gdf = gdf.simplify(0.005, preserve_topology=True)
    poly = orient(gdf.loc[0], sign=1.0)

    geojson = gpd.GeoSeries(poly).to_json()  # Convert to geojson
    geojson = geojson.replace(" ", "")  # remove spaces for API call

    # Format dictionary to polygon coordinate pairs for CMR polygon filtering
    polygon = ",".join([str(c) for xy in zip(*poly.exterior.coords.xy) for c in xy])
    return polygon, geojson


def _request_capabilities(
    session,
    product_short_name,
    latest_version,
    uid,
    pswd,
    aoi,
    geojson,
    bounding_box="",
):
    capability_url = f"https://n5eil02u.ecs.nsidc.org/egi/capabilities/{product_short_name}.{latest_version}.xml"
    s = session.get(capability_url)
    response = session.get(s.url, auth=(uid, pswd))

    root = ET.fromstring(response.content)

    # collect lists with each service option

    subagent = [subset_agent.attrib for subset_agent in root.iter("SubsetAgent")]
    if len(subagent) > 0:

        # variable subsetting
        variables = [
            SubsetVariable.attrib for SubsetVariable in root.iter("SubsetVariable")
        ]
        variables_raw = [variables[i]["value"] for i in range(len(variables))]
        variables_join = [
            "".join(("/", v)) if v.startswith("/") == False else v
            for v in variables_raw
        ]
        variable_vals = [v.replace(":", "/") for v in variables_join]

        # reformatting
        formats = [Format.attrib for Format in root.iter("Format")]
        format_vals = [formats[i]["value"] for i in range(len(formats))]
        format_vals.remove("")

        # reprojection options
        projections = [Projection.attrib for Projection in root.iter("Projection")]

    if len(subagent) < 1:
        print("No services exist for", product_short_name, "version", latest_version)
        agent = "NO"
        bbox = ""
        time_var = ""
        reformat = ""
        projection = ""
        projection_parameters = ""
        coverage = ""
        Boundingshape = ""
    else:
        agent = ""
        subdict = subagent[0]
        if subdict["spatialSubsetting"] == "true" and aoi == "bounding_box":
            Boundingshape = ""
            ss = "y"
            if ss == "y":
                bbox = bounding_box
            else:
                bbox = ""
        if subdict["spatialSubsettingShapefile"] == "true" and aoi == "shapefile":
            # raise NotImplementedError("shapefile downloading is broken right now")
            bbox = ""
            ps = "y"
            if ps == "y":
                Boundingshape = geojson
            else:
                Boundingshape = ""
        if subdict["temporalSubsetting"] == "true":
            ts = "n"
            if ts == "y":
                time_var = (
                    start_date + "T" + start_time + "," + end_date + "T" + end_time
                )
            else:
                time_var = ""
        else:
            time_var = ""
        if len(format_vals) > 0:
            print("These reformatting options are available:", format_vals)
            reformat = "NetCDF4-CF"
            if reformat == "n":
                reformat = ""  # Catch user input of 'n' instead of leaving blank
        else:
            reformat = ""
            projection = ""
            projection_parameters = ""
        if len(projections) > 0:
            valid_proj = (
                []
            )  # select reprojection options based on reformatting selection
            for i in range(len(projections)):
                if "excludeFormat" in projections[i]:
                    exclformats_str = projections[i]["excludeFormat"]
                    exclformats_list = exclformats_str.split(",")
                if (
                    "excludeFormat" not in projections[i]
                    or reformat not in exclformats_list
                ) and projections[i]["value"] != "NO_CHANGE":
                    valid_proj.append(projections[i]["value"])
            if len(valid_proj) > 0:
                print(
                    "These reprojection options are available with your requested format:",
                    valid_proj,
                )
                projection = input(
                    "If you would like to reproject, copy and paste the reprojection option you would like (make sure to omit quotes), otherwise leave blank."
                )
                # Enter required parameters for UTM North and South
                if (
                    projection == "UTM NORTHERN HEMISPHERE"
                    or projection == "UTM SOUTHERN HEMISPHERE"
                ):
                    NZone = input(
                        "Please enter a UTM zone (1 to 60 for Northern Hemisphere; -60 to -1 for Southern Hemisphere):"
                    )
                    projection_parameters = str("NZone:" + NZone)
                else:
                    projection_parameters = ""
            else:
                print(
                    "No reprojection options are supported with your requested format"
                )
                projection = ""
                projection_parameters = ""
        else:
            print("No reprojection options are supported with your requested format")
            projection = ""
            projection_parameters = ""
    if (
        reformat == ""
        and projection == ""
        and projection_parameters == ""
        and coverage == ""
        and time_var == ""
        and bbox == ""
        and Boundingshape == ""
    ):
        agent = "NO"
    return (
        reformat,
        projection,
        projection_parameters,
        time_var,
        bbox,
        Boundingshape,
        agent,
    )


def _data_search(product_short_name, bounding_box, temporal, bounds_filepath=None):

    latest_version = _get_product_metadata(product_short_name)

    print(f"The most recent version of {product_short_name} is {latest_version}")

    # %%
    # Input temporal range

    # start_date = input('Input start date in yyyy-MM-dd format: ')
    # start_time = input('Input start time in HH:mm:ss format: ')
    # end_date = input('Input end date in yyyy-MM-dd format: ')
    # end_time = input('Input end time in HH:mm:ss format: ')

    # temporal = start_date + 'T' + start_time + 'Z' + ',' + end_date + 'T' + end_time + 'Z'

    search_params = {
        "short_name": product_short_name,
        "version": latest_version,
        "temporal": temporal,
        "page_size": 100,
        "page_num": 1,
        "bounding_box": bounding_box,
    }

    if bounding_box == "":
        aoi = "shapefile"
        polygon, geojson = _prepare_geo_file(bounds_filepath=bounds_filepath)
        search_params["polygon"] = polygon
    else:
        aoi = "bounding_box"
        search_params["bounding_box"] = geojson
        search_params["polygon"] = polygon
        polygon = ""
        geojson = ""

    granules = []
    headers = {"Accept": "application/json"}
    while True:
        response = requests.get(
            GRANULE_SEARCH_URL, params=search_params, headers=headers
        )
        results = json.loads(response.content)
        if len(results["feed"]["entry"]) == 0:
            # Out of results, so break out of loop
            break

        # Collect results and increment page_num
        granules.extend(results["feed"]["entry"])
        search_params["page_num"] += 1

    print(
        "There are",
        len(granules),
        "granules of",
        product_short_name,
        "version",
        latest_version,
        "over my area and time of interest.",
    )
    granule_sizes = [float(granule["granule_size"]) for granule in granules]

    print(
        f"The average size of each granule is {mean(granule_sizes):.2f} MB and the total size of all {len(granules)} granules is {sum(granule_sizes):.2f} MB"
    )

    return latest_version, aoi, polygon, geojson, granules


def _request_async_func(page_num, session, param_dict, base_url, path):
    param_dict["request_mode"] = "async"
    # Request data service for each page number, and unzip outputs
    # print(page_num,session,param_dict,base_url)
    for page_val in range(1, page_num + 1):
        print("Order: ", page_val)
        # For all requests other than spatial file upload, use get function
        request = session.get(base_url, params=param_dict)
        print("Request HTTP response: ", request.status_code)

        # Raise bad request: Loop will stop for bad response code.
        request.raise_for_status()
        print("Order request URL: ", request.url)
        esir_root = ET.fromstring(request.content)
        # print("Order request response XML content: ", request.content)

        # Look up order ID
        orderlist = []
        for order in esir_root.findall("./order/"):
            orderlist.append(order.text)
        orderID = orderlist[0]
        print("order ID: ", orderID)

        # Create status URL
        statusURL = base_url + "/" + orderID
        print("status URL: ", statusURL)

        # Find order status
        request_response = session.get(statusURL)
        print("HTTP response from order response URL: ", request_response.status_code)

        # Raise bad request: Loop will stop for bad response code.
        request_response.raise_for_status()
        request_root = ET.fromstring(request_response.content)
        statuslist = []
        for status in request_root.findall("./requestStatus/"):
            statuslist.append(status.text)
        status = statuslist[0]
        print("Data request ", page_val, " is submitting...")
        print("Initial request status is ", status)

        # Continue loop while request is still processing
        while status == "pending" or status == "processing":
            print("Status is not complete. Trying again.")
            time.sleep(10)
            loop_response = session.get(statusURL)

            # Raise bad request: Loop will stop for bad response code.
            loop_response.raise_for_status()
            loop_root = ET.fromstring(loop_response.content)

            # find status
            statuslist = []
            for status in loop_root.findall("./requestStatus/"):
                statuslist.append(status.text)
            status = statuslist[0]
            print("Retry request status is: ", status)
            if status == "pending" or status == "processing":
                continue

        # Order can either complete, complete_with_errors, or fail:
        # Provide complete_with_errors error message:
        if status == "complete_with_errors" or status == "failed":
            messagelist = []
            for message in loop_root.findall("./processInfo/"):
                messagelist.append(message.text)
            print("error messages:")
            pprint.pprint(messagelist)

        # Download zipped order if status is complete or complete_with_errors
        if status == "complete" or status == "complete_with_errors":
            downloadURL = "https://n5eil02u.ecs.nsidc.org/esir/" + orderID + ".zip"
            print("Zip download URL: ", downloadURL)
            print("Beginning download of zipped output...")
            zip_response = session.get(downloadURL)
            # Raise bad request: Loop will stop for bad response code.
            zip_response.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(zip_response.content)) as z:
                z.extractall(path)
            print("Data request", page_val, "is complete.")
        else:
            print("Request failed.")


def _request_streaming(page_num, session, param_dict, base_url, path):
    print("entering streaming request function")
    param_dict["request_mode"] = "stream"
    print("Starting Streaming request with param dict", param_dict)
    # print(param_dict)
    for page_val in range(1, page_num + 1):
        print("Order: ", page_val)
        print("Requesting...")
        request = session.get(base_url, params=param_dict)
        print(request.headers)
        print(request.url)
        print("HTTP response from order response URL: ", request.status_code)
        request.raise_for_status()
        d = request.headers["content-disposition"]
        fname = re.findall("filename=(.+)", d)

        dirname = os.path.join(path, fname[0].strip('"'))
        print("Downloading...")
        with open(dirname, "wb") as outfolder:
            outfolder.write(request.content)
        print("Data request", page_val, "is complete.")


def _unzip_output_file(path):
    for z in os.listdir(path):
        if z.endswith(".zip"):
            zip_name = path + "/" + z
            zip_ref = zipfile.ZipFile(zip_name)
            zip_ref.extractall(path)
            zip_ref.close()
            os.remove(zip_name)


def _clean_output_folders(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for file in files:
            try:
                shutil.move(os.path.join(root, file), path)
            except OSError:
                pass
        for name in dirs:
            os.rmdir(os.path.join(root, name))


def request_data_download(
    product_short_name, bounding_box, folderpath, vars_, bounds_filepath=None
):

    uid = EARTHDATA_USERNAME  # Enter Earthdata Login user name
    pswd = EARTHDATA_PASSWORD  # Enter Earthdata Login password
    email = EMAIL  # Enter Earthdata login email

    temporal = ""

    latest_version, aoi, polygon, geojson, granules = _data_search(
        product_short_name=product_short_name,
        bounding_box=bounding_box,
        bounds_filepath=bounds_filepath,
        temporal=temporal,
    )

    # Create session to store cookie and pass credentials to capabilities url
    session = requests.session()

    (
        reformat,
        projection,
        projection_parameters,
        time_var,
        bbox,
        Boundingshape,
        agent,
    ) = _request_capabilities(
        session,
        product_short_name=product_short_name,
        latest_version=latest_version,
        uid=uid,
        pswd=pswd,
        aoi=aoi,
        geojson=geojson,
    )
    coverage = vars_
    # Set the request mode to asynchronous if the number of granules is over 100, otherwise synchronous is enabled by default
    if len(granules) > 100:
        request_async = True
        page_size = 2000
    else:
        page_size = 100
        request_async = False

    # Determine number of orders needed for requests over 2000 granules.
    page_num = math.ceil(len(granules) / page_size)

    print(
        "There will be",
        page_num,
        "total order(s) processed for our",
        product_short_name,
        "request.",
    )
    # generic param_dict
    param_dict = {
        "short_name": product_short_name,
        "version": latest_version,
        "temporal": temporal,
        "time": time_var,
        "format": reformat,
        "projection": projection,
        "projection_parameters": projection_parameters,
        "Coverage": coverage,
        "page_size": page_size,
        "agent": agent,
        "email": email,
    }
    if aoi == "bounding_box":
        # bounding box search and subset:
        param_dict["bounding_box"] = bounding_box
        param_dict["Bbox"] = bounding_box
    elif aoi == "shapefile":
        param_dict["Boundingshape"] = geojson
        param_dict["polygon"] = polygon

    # TODO could reverse this by setting up the dictionary based on available parameters
    # maybe using a function that only takes kw args

    # Remove blank key-value-pairs
    param_dict = {k: v for k, v in param_dict.items() if v != ""}

    # Convert to string
    param_string = "&".join("{!s}={!r}".format(k, v) for (k, v) in param_dict.items())
    param_string = param_string.replace("'", "")

    # Print API base URL + request parameters
    endpoint_list = []
    for page_val in range(1, page_num + 1):
        API_request = f"{BASE_URL}?{param_string}&page_num={page_val}"
        endpoint_list.append(API_request)

    # print("ENDPOINTLIST: ", *endpoint_list, sep="\n")

    path = folderpath + "/" + product_short_name
    if not os.path.exists(path):
        os.mkdir(path)

    if request_async:
        print("requesting async")
        _request_async_func(page_num, session, param_dict, BASE_URL, path)
    else:
        _request_streaming(page_num, session, param_dict, BASE_URL, path)
        _unzip_output_file(path)

    _clean_output_folders(path)


def request_segments_only(shapefile_filepath, folderpath):
    request_data_download(
        "ATL03",
        vars_=segment_vars,
        bounds_filepath=shapefile_filepath,
        bounding_box="",
        folderpath=folderpath,
    )


def request_full_data_shapefile(shapefile_filepath, folderpath):
    request_data_download(
        "ATL03",
        vars_=atl_03_vars,
        bounds_filepath=shapefile_filepath,
        bounding_box="",
        folderpath=folderpath,
    )


# TODO run and debug as needed
# might require some significant abstraction of the request_data_download function
def request_ATL09_shapefile(bounds_filepath, folderpath):
    request_data_download(
        "ATL09",
        vars_=atl_03_vars,
        bounds_filepath=bounds_filepath,
        bounding_box="",
        folderpath=folderpath,
    )


if __name__ == "__main__":

    request_full_data_shapefile(
        shapefile_filepath="../data/test_sites/florida_keys/AOI.shp",
        folderpath="../data/test_sites/florida_keys/atl03_new",
    )
