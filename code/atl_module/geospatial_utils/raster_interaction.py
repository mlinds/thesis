from os.path import basename
from subprocess import PIPE, Popen

import geopandas as gpd
import numpy as np
import pandas as pd

# from pyproj import transform
import rasterio as rio
from logzero import logger, setup_logger
from osgeo import gdal

gdal.UseExceptions()
# TODO this needs to be refactored to use rasterio since import gdal and rasterio can cause issues


detail_logger = setup_logger(name="details")


def _assign_na_values(inpval):
    # this could be inlined into a lambda function, and made to predict the nodata value
    """
    assign the appropriate value to the output of the gdallocationinfo response. '-99999' and an empty string are NaN values

    Anything else will return the input coerced to a float
    """
    return np.NaN if inpval in ["", "-999999", "-9999"] else float(inpval)


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
    # take x,y pairs from dataframe, convert to a big string, then into a bytestring to feed into the pipe ##

    # first we take the coordinates and combine them as strings
    coordlist = "".join([f"{x} {y} " for x, y in xylist.tolist()])

    # convert string to a bytestring to keep GDAL happy
    pipeinput = bytes(coordlist, "utf-8")

    # gdal location info command with arguments
    cmd = ["gdallocationinfo", "-wgs84", "-valonly", "-b", "1", src]
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


# TODO change this function to take the bounds as in input instead of the dataframe
def subset_gebco(folderpath: str, bathy_pts, epsg_no: int, hres: int):
    """Create a resampled (bilinearly) and reprojected subset of the global GEBCO dataset. Write it to the same input folder

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

    # get the boundaries in WGS coordinates
    bounds_wgs84 = bathy_pts.to_crs("EPSG:4326").geometry.total_bounds
    # get the number of the EPSG crs (should be the local UTM zone!!)

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
        outputType=gdal.GDT_Float32,
        # format='GTiff'
    )
    ds = gdal.Warp(out_raster_path, GEBCO_LOCATION, options=options)
    print(ds)
    ds = None

    # reopen with rasterio to mask out the values out of range
    with rio.open(out_raster_path, mode="r+") as reprojected_raster:
        raw_data = reprojected_raster.read(1, masked=True)
        # set values outside of our range to nan
        raw_data[raw_data > 2] = np.NaN
        raw_data[raw_data < -40] = np.NaN
        reprojected_raster.write(raw_data, 1)

    logger.debug(f"GEBCO subset raster written to {out_raster_path}, with CRS EPSG:{epsg_no}")

    # # ------------ below this is expermental code---------------
    # with rio.open(GEBCO_LOCATION, mode="r",crs="EPSG:4326") as gebco:
    #     print('crs of gebco: ',gebco.crs)
    #     window = rio.windows.from_bounds(*bounds_wgs84, transform=gebco.transform)
    #     print(window)
    #     print(bounds_wgs84)
    #     gebco_data = gebco.read(1, window=window, masked=True)
    #     gebco_data[gebco_data > 2] = gebco.nodata
    #     gebco_data[gebco_data < -40] = gebco.nodata

    #     with rio.io.MemoryFile() as memfile:
    #         newmetadata = gebco.meta.copy()
    #         print(newmetadata)
    #         with memfile.open():
    #             pass
    #     return None


def raster_random_sample(raster_in, nsample_points, crs=None):

    with rio.open(raster_in) as inraster:
        # we can rewrite the supplied values
        crs = inraster.crs
        if crs is None:
            raise ValueError(
                "The supplied raster has no CRS information. Please supply a CRS when calling the function"
            )
        # get a 1d array of xcoords and ycoords within the bounds of the input raster:
        xsample = np.random.uniform(
            low=inraster.bounds.left, high=inraster.bounds.right, size=nsample_points
        )
        ysample = np.random.uniform(
            low=inraster.bounds.bottom, high=inraster.bounds.top, size=nsample_points
        )
        # make a list of coordinate tuples
        samplecoords = [(x, y) for x, y in zip(xsample, ysample)]
        # get the z values
        zsample = np.array(list(inraster.sample(samplecoords, indexes=1, masked=True)))
        # print(inraster.nodata)
        zsample_nodata_removed = np.ma.masked_values(zsample, inraster.nodata)

        # get just the max to use for indexing the other arrays
        nodatamask = zsample_nodata_removed.mask[:, 0]
        # get the values where the numpy ma mask is False
        xsample_out = xsample[~nodatamask]
        ysample_out = ysample[~nodatamask]
        zsample_out = zsample[~nodatamask][:, 0]

    return crs, xsample_out, ysample_out, zsample_out
    # return nodatamask


def random_raster_gdf(raster_in, nsample_points_required):
    # since some points will be in outside of the valid data mask, we need to sample more points than we need in the end.
    first_guess = nsample_points_required * 2
    crs, x, y, z = raster_random_sample(raster_in=raster_in, nsample_points=first_guess)

    # if we have less points than we need, we will try again
    while len(x) < nsample_points_required:
        crs, x_loop, y_loop, z_loop = raster_random_sample(
            raster_in=raster_in, nsample_points=nsample_points_required
        )

        x = np.append(x, x_loop)
        y = np.append(y, y_loop)
        z = np.append(z, z_loop)

    gdf = (
        gpd.GeoDataFrame(
            {"truth raster elevation": z}, geometry=gpd.points_from_xy(x, y, crs=crs)
        )
        .to_crs("EPSG:4326")
        .sample(nsample_points_required)
        .reset_index(drop=True)
    )

    return gdf
