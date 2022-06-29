from os.path import basename
from subprocess import PIPE, Popen

import numpy as np
import pandas as pd


def _assign_na_values(inpval):
    # this could be inlined into a lambda function, and made to predict the nodata value
    """
    assign the appropriate value to the output of the gdallocationinfo response. '-99999' and an empty string are NaN values

    Anything else will return the input coerced to a float
    """
    return np.NaN if inpval in ["", "-999999"] else float(inpval)


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
    cmd = ["gdallocationinfo", "-geoloc", "-valonly", src]
    # open a pipe to these commands
    with Popen(cmd, stdout=PIPE, stdin=PIPE) as p:
        # feed in our bytestring
        out, err = p.communicate(input=pipeinput)
    outlist = out.decode("utf-8").split("\n")
    # go through and assign NA values as needed. Also discard the extra empty line that the split command induces
    return [_assign_na_values(inpval) for inpval in outlist[:-1]]


def add_dem_data(beam_df: pd.DataFrame, demlist: list) -> pd.DataFrame:

    for dempath in demlist:
        demname = basename(dempath).split(".")[0]
        values_at_pt = query_raster(beam_df, dempath)
        beam_df.loc[:, (demname)] = values_at_pt

    return beam_df
