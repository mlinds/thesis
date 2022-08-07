import glob
from os import PathLike

import geopandas as gpd
import numpy as np
import pandas as pd
from atl_module.io.atl03_netcdf_loading import get_beams, load_beam_array_ncds
from logzero import setup_logger
from shapely.geometry import LineString, Point

detail_logger = setup_logger(name="details")


def to_refr_corrected_gdf(df, crs):
    """Take the original gdf of the bathymetry points, translate them to the local UTM zone, and changes the points based on the calculated refraction

    Args:
        df (pd.DataFrame): input point dataframe
        crs (str): crs string or CRS object

    Returns:
        pd.DataFram: dataframe with the corrected data
    """
    # make the geometry of the horizontallly corrected point locations
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.X, df.Y), crs="EPSG:4326")
    reprojected = gdf.to_crs(crs)
    easting = reprojected.geometry.x
    northing = reprojected.geometry.y
    geometry = gpd.points_from_xy(
        (easting + df.easting_corr), (northing + df.northing_corr), crs=crs
    )
    return gpd.GeoDataFrame(df, geometry=geometry).assign(
        easting_raw=easting, northing_raw=northing
    )


def get_track_gdf(outarray: np.ndarray) -> gpd.GeoDataFrame:
    """Create a geodataframe for a track as defined by an array of photon returns

    Args:
        outarray (np.ndarray): structured array of photon locations

    Returns:
        gpd.GeoDataFrame: A geodataframe of a particular track
    """
    linegeom = _get_single_track_linegeom(outarray)
    return gpd.GeoDataFrame(
        {"geometry": [linegeom]}, crs="EPSG:4326", geometry="geometry"
    )


def _get_single_track_linegeom(beamarray: np.ndarray) -> LineString:
    if beamarray is not None:
        ymin = beamarray["Y"].min()
        xmin = beamarray["X"][beamarray["Y"].argmin()]
        ymax = beamarray["Y"].max()
        xmax = beamarray["X"][beamarray["Y"].argmax()]
        coords = [
            [xmin, ymin],
            [xmax, ymax],
        ]
        # print(coords)
        return LineString(coords)


def make_gdf_from_ncdf_files(directory: str or PathLike) -> gpd.GeoDataFrame:
    """Generates a GeoDataFrame of all the tracks in a given folder, with information about the date and the quality

    Args:
        directory (strorPathLike): Location of the folder to search for netcdf files

    Returns:
        gpd.GeoDataFrame: Dataframe containing all the tracks of interest, projected in local UTM coodrinate system
    """
    # TODO: fix this unreadable function
    # try to decrease the indent level - itertools?
    beamlist = []
    datelist = []
    rgtlist = []
    filenamelist = []
    geomlist = []
    beam_type_list = []
    # percent_high_conf = []
    for h5file in glob.iglob(directory):

        filefriendlyname = str(h5file.split("/")[-1]).strip(".nc")

        # all list writes need to be inside this loop
        for beam in get_beams(h5file):
            # get the point array and make it into a linestring
            point_array = load_beam_array_ncds(h5file, beam)
            track_geom = _get_single_track_linegeom(point_array)

            # write to all the lists
            # we can stack this into a multiindex later

            filenamelist.append(filefriendlyname)
            beamlist.append(beam)
            geomlist.append(track_geom)

            if point_array is None:
                rgtlist.append(np.NaN)
                datelist.append(np.NaN)
                # percent_high_conf.append(np.NaN)
            else:
                rgt = point_array.dtype.metadata["start_rgt"]
                date = point_array.dtype.metadata["data_start_utc"]
                beamtype = point_array.dtype.metadata["atlas_beam_type"]
                # p_oc_h_conf = point_array.dtype.metadata["ocean_high_conf_perc"]
                rgtlist.append(rgt)
                datelist.append(date)
                beam_type_list.append(beamtype)
                # percent_high_conf.append(p_oc_h_conf)
    # get geodataframe in same CRS as icessat data
    gdf = gpd.GeoDataFrame(
        {
            "file": filenamelist,
            "geometry": geomlist,
            "Reference Ground Track": rgtlist,
            "date": datelist,
            "beam": beamlist,
            "beam_type": beam_type_list,
            # "Percentage High confidence Ocean Returns": percent_high_conf,
        },
        crs="EPSG:4326",
        geometry="geometry",
    ).set_index(["file", "beam"])

    # prooject it to the appropriate UTM system
    # crs_UTM = gdf.estimate_utm_crs()
    # gdf.to_crs(crs_UTM, inplace=True)
    return gdf


def photon_df_to_gdf(photon_data: pd.DataFrame or np.ndarray):
    pass


def add_track_dist_meters(
    # y is lat, x is lon
    df: pd.DataFrame,
    geodataframe=False,
) -> pd.DataFrame or gpd.GeoDataFrame:
    xcoords = df["X"]
    ycoords = df["Y"]
    geom = gpd.points_from_xy(xcoords, ycoords, crs="EPSG:4326")
    gdf = gpd.GeoDataFrame(df, geometry=geom, crs="EPSG:4326")
    # to find distance in meters we need to estimate the UTM zone required
    utmzone = gdf.estimate_utm_crs()
    # convert to the UTM zone we found
    gdf = gdf.to_crs(utmzone)
    ymin = gdf.geometry.y.min()
    xmin = gdf.geometry.x[gdf.geometry.y.argmin()]

    # returns a vector of the dist from the start point (the start point being (xmin,ymin))
    dist = gdf.distance(Point(xmin, ymin))
    # add the new distance
    gdf = gdf.assign(
        dist_or=dist, easting=gdf.geometry.x, northing=gdf.geometry.y
    ).sort_values("dist_or")
    # return a dataframe or GDF
    return gdf if geodataframe else pd.DataFrame(gdf.drop(columns="geometry"))
