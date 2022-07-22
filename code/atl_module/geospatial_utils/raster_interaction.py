from os.path import basename
from subprocess import PIPE, Popen

import numpy as np
import pandas as pd
import rasterio as rio
from logzero import setup_logger, logger
from osgeo import gdal

detail_logger = setup_logger(name="details")


def _assign_na_values(inpval):
    # this could be inlined into a lambda function, and made to predict the nodata value
    """
    assign the appropriate value to the output of the gdallocationinfo response. '-99999' and an empty string are NaN values

    Anything else will return the input coerced to a float
    """
    return np.NaN if inpval in ["", "-999999","-9999"] else float(inpval)


# function that gets values from rasters for each lidar photon
def query_raster(dataframe: pd.DataFrame, src: str):
    """Takes a dataframe with a column named X and Y (WITH WGSLATLONGS) and a raster file, and returns the raster value at each point X and Y

    Args:
        dataframe (pd.DataFrame): Column with X and Y values, in the same CRS as the raster
        src (str): PathLike string that is the path of the raster to query

    Returns:
        ndarray: 1D Array of values at each point.
    """
    # TODO maybe adjust this to deal with the refraction-corrected locations. Might make a very small difference
    # but any accuracy gain might be offset by the the uncertainty in the transforms when going from easting/norting to geographic coordinates

    # takes a dataframe of points, and any GDAL raster as input
    xylist = dataframe.loc[:, ["X", "Y"]].values
    ## take x,y pairs from dataframe, convert to a big string, then into a bytestring to feed into the pipe ##

    # first we take the coordinates and combine them as strings
    coordlist = "".join([f"{x} {y} " for x, y in xylist.tolist()])

    # convert string to a bytestring to keep GDAL happy
    pipeinput = bytes(coordlist, "utf-8")

    # gdal location info command with arguments
    cmd = ["gdallocationinfo", "-wgs84", "-valonly", src]
    # open a pipe to these commands
    with Popen(cmd, stdout=PIPE, stdin=PIPE) as p:
        # feed in our bytestring
        out, err = p.communicate(input=pipeinput)
    outlist = out.decode("utf-8").split("\n")
    # go through and assign NA values as needed. Also discard the extra empty line that the split command induces
    # TODO this could be changed to use filter() and automatically 
    return [_assign_na_values(inpval) for inpval in outlist[:-1]]


# TODO maybe delete
def add_dem_data(beam_df: pd.DataFrame, demlist: list) -> pd.DataFrame:

    for dempath in demlist:
        demname = basename(dempath).split(".")[0]
        values_at_pt = query_raster(beam_df, dempath)
        beam_df.loc[:, (demname)] = values_at_pt

    return beam_df


def subset_gebco(folderpath:str, tracklines, epsg_no:int,hres:int):
    """Create a resampled (bilinearly) and reprojected subset of the global GEBCO dataset. Write it to the same input folder
        NB. IMPURE FUNCTION

    Args:
        folderpath (str): The root folder of the test site
        tracklines (gpd.GeoDataFrame): The tracklines geodataframe object
        epsg_no (int): The integer number of the EPSG code for the desired CRS
        hres (int): The horizontal (x and y) resolution of the resampled image

    Returns:
        None
    """    
    # TODO mask first, before interpolation

    # constant that defines location of the GEBCO raster
    GEBCO_LOCATION = "/mnt/c/Users/XCB/OneDrive - Van Oord/Documents/thesis/data/GEBCO/GEBCO_2021_sub_ice_topo.nc"
    # get the trackline GDF
    # tracklines = gpd.read_file(f"{folderpath}/tracklines.gpkg")
    # get the boundaries
    # bounds_utm = tracklines.geometry.total_bounds
    bounds_wgs84 = tracklines.to_crs("EPSG:4326").geometry.total_bounds
    # get the number of the EPSG crs (should be the local UTM zone!!)
    # epsg_no = tracklines.crs.to_epsg()

    out_raster_path = f"{folderpath}/bilinear.tif"
    options = gdal.WarpOptions(
        outputBounds=bounds_wgs84,
        outputBoundsSRS="EPSG:4326",
        srcSRS="EPSG:4326",
        dstSRS=f"EPSG:{epsg_no}",
        xRes=hres,
        yRes=hres,
        resampleAlg="bilinear",
        srcNodata=-32767,
        dstNodata=-999999,
        outputType=gdal.GDT_Float64,
        # format='GTiff'
    )
    ds = gdal.Warp(out_raster_path, GEBCO_LOCATION, options=options)
    ds = None

    # reopen with rasterio to mask out the values out of range
    with rio.open(out_raster_path, mode="r+") as reprojected_raster:
        raw_data = reprojected_raster.read(1, masked=True)
        raw_data[raw_data > 2] = np.NaN
        raw_data[raw_data < -40] = np.NaN
        reprojected_raster.write(raw_data, 1)

    logger.debug(
        f"GEBCO subset raster written to {out_raster_path}, with CRS EPSG:{epsg_no}"
    )
    return None
