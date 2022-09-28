from datetime import datetime

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import xarray as xr
from atl_module.secret_vars import COPERNICUS_PW, COPERNICUS_USERNAME

DAP_URL = "https://my.cmems-du.eu/thredds/dodsC/cmems_obs-oc_glo_bgc-transp_my_l4-gapfree-multi-4km_P1D"


# setup the session upon import
def _setup_globcolor_api_session(COPERNICUS_USERNAME: str, COPERNICUS_PW: str, DAP_URL: str):
    """Create a dataset of the GlobColour Data using the correct login. The xarray dataset uses lazy loading so it can be generated then values can be looked up as needed.

    Args:
        COPERNICUS_USERNAME (str): MarineData username
        COPERNICUS_PW (str): Marinedata password
        DAP_URL (str): URL of the required dataset

    Returns:
        xr.Dataset: xarray dataset with the required data.
    """
    # start a new https session with basic http authentication
    session = requests.session()
    session.auth = (COPERNICUS_USERNAME, COPERNICUS_PW)
    # create a datastore that xarray can consume
    store = xr.backends.PydapDataStore.open(DAP_URL, session=session)
    return xr.open_dataset(store)


ds = _setup_globcolor_api_session(COPERNICUS_USERNAME, COPERNICUS_PW, DAP_URL)


def get_zsd_info(lat: float, lon: float, dates: str or datetime) -> tuple:

    """lookup the disk depth info at a certain location and time.

    Args:
        lat (float): latitude in WGS84
        lon (float): longitude in WGS84
        dates (strordatetime): A string or numpy/python datetime object for a date

    Returns:
        tuple: tuple of (Disk Depth, Disk Depth uncertainty)
    """
    # required to used a dataarray to get a vectorized index
    lat_indexer = xr.DataArray(lat, dims=["points"])
    lon_indexer = xr.DataArray(lon, dims=["points"])
    date_indexer = xr.DataArray(dates, dims=["points"])
    # load the nearest data within 0.1 degrees of the requested point
    subset = ds.sel(lat=lat_indexer, lon=lon_indexer, method="nearest",).sel(  # tolerance=0.1
        # load the nearest time within 2 days
        time=date_indexer,
        method="nearest",
        tolerance=2,
    )
    # get an array of depth and uncertainty
    secchi_depth_array = subset.ZSD.to_numpy()
    secchi_depth_uncertainty_array = subset.ZSD_uncertainty.to_numpy()
    diffuse_attenuation_array = subset.KD490.to_numpy()
    diffuse_attenuation_unc_array = subset.KD490_uncertainty
    return (
        secchi_depth_array,
        secchi_depth_uncertainty_array,
        diffuse_attenuation_array,
        diffuse_attenuation_unc_array,
    )


def _resample_line(linestring):
    distances = np.arange(0, linestring.length, 0.025)
    points = [linestring.interpolate(distance) for distance in distances] + [
        linestring.boundary[1]
    ]
    return points


def create_zsd_points_from_tracklines(df_input):

    # change the datetime to only the nearest day
    df_input["date"] = pd.to_datetime(df_input.date).dt.date
    # empty list to keep the points and their dates
    allpts = []
    # loop over each trackline
    for trackline in df_input.itertuples():
        points = _resample_line(trackline.geometry)
        # print(trackline)
        date_points = [[trackline.date, pointgeom, trackline.beam] for pointgeom in points]
        allpts = allpts + date_points
    sample_pts_gdf = gpd.GeoDataFrame(
        allpts,
        geometry="geometry",
        columns=["date", "geometry", "beam"],
        crs="EPSG:4326",
    )
    # get the actualy secchi depth info
    a, b, c, d = get_zsd_info(
        sample_pts_gdf.geometry.y, sample_pts_gdf.geometry.x, sample_pts_gdf.date
    )
    sample_pts_gdf = sample_pts_gdf.assign(
        zsd=a,
        sigma_zsd=b,
        diff_atten=c,
        diff_atten_unc=d,
        date=pd.to_datetime(sample_pts_gdf.date),
    )
    return sample_pts_gdf
