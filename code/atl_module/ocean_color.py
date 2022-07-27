from datetime import datetime

import geopandas as gpd
import pandas as pd
import requests
import xarray as xr

from atl_module.secret_vars import COPERNICUS_PW, COPERNICUS_USERNAME

DAP_URL = "https://my.cmems-du.eu/thredds/dodsC/cmems_obs-oc_glo_bgc-transp_my_l4-gapfree-multi-4km_P1D"

# setup the session upon import
def _setup_globcolor_api_session(
    COPERNICUS_USERNAME: str, COPERNICUS_PW: str, DAP_URL: str
) -> xr.Dataset:
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


# create the dataset when the module is imported
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
    # load the nearest data within 0.2 degrees of the requested point
    subset = ds.sel(
        lat=lat_indexer, lon=lon_indexer, method="nearest", tolerance=0.1
    ).sel(
        # load the nearest time within 2 days
        time=date_indexer,
        method="nearest",
        tolerance=2,
    )
    # get an array of depth and uncertainty
    secchi_depth_array = subset.ZSD.to_numpy()
    secchi_depth_uncertainty_array = subset.ZSD_uncertainty.to_numpy()
    return secchi_depth_array, secchi_depth_uncertainty_array
    # return secchi_depth_array


def get_color_dataframe(lat, lon, dates):
    # select the latitude and longitude
    subset = ds.sel(
        lat=lat,
        lon=lon,
        method="nearest"
        # get the closest date
    ).sel(time=dates, method="nearest")
    return subset.to_dataframe()


def add_secchi_depth_to_tracklines(df_input: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Accepts a dataframe of tracklines and returns the same dataframe with a new column for the Secchi Disk Depth and the uncertainty

    Args:
        df_input (gpd.GeoDataFrame): Geodataframe of the tracklines

    Returns:
        gpd.GeoDataFrame: Same geodataframe with 2 new columns
    """
    # create a temporary reprojected version of the dataframe

    temp = df_input.assign(
        xcoord=df_input.to_crs("EPSG:4326").centroid.x,
        ycoord=df_input.to_crs("EPSG:4326").centroid.y,
        date=pd.to_datetime(df_input.date).dt.date,
    )
    # get a series of the depth and uncertainty values
    zsd_vals, zsd_sigma_vals = get_zsd_info(
        temp.ycoord.values, temp.xcoord.values, temp.date.values
    )
    # add the series to the original dataframe and return
    return df_input.assign(
        secchi_depth=zsd_vals,
        secchi_depth_unc=zsd_sigma_vals,
    )
