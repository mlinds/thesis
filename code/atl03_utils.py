import json
from enum import Enum

import geopandas as gpd
import numpy as np
import pandas as pd
import pdal
import xarray as xr
from netCDF4 import Dataset, MFDataset
from shapely.geometry import LineString
from sklearn.cluster import DBSCAN

beamlist = ["gt1l", "gt1r", "gt2l", "gt2r", "gt3l", "gt3r"]

# i'm super lazy and just made this to autocomplete the beam names when typing
class Beams:
    gt1l = "gt1l"
    gt1r = "gt1r"
    gt2l = "gt2l"
    gt2r = "gt2r"
    gt3l = "gt3l"
    gt3r = "gt3r"


def min_dbscan_points(oned_pt_array_in):
    """Get the minimmum points parameter for DBSCAN as defined in Ma et al 2021


    Args:
        oned_pt_array_in (np.array): Numpy Structured array as returned by PDAL pipeline

    Returns:
        float: The minimum cluster size for DBSCAN
    """    
    N1 = oned_pt_array_in.shape[0]
    Ra = 1.5
    h = oned_pt_array_in['Y'].max() - oned_pt_array_in['Y'].min()
    l = oned_pt_array_in['tr_d'].max() - oned_pt_array_in['tr_d'].min()
    # find the boundary for the lowest 5m
    zlim = oned_pt_array_in['Z'].min() + 5
    # anything below that gets counted as above
    N2 = oned_pt_array_in['Z'][oned_pt_array_in['Z']<zlim].shape[0]
    SN1 = (np.pi*Ra**2*N1)/(h*l)
    SN2 = (np.pi*Ra**2*N2)/(5*l)
    minpoints = (2*SN1-SN2)/np.log((2*SN1/SN2))
    return minpoints

def get_beams(granule_netcdf):
    """List the beams available for a given granule

    Args:
        granule_netcdf (Pathlike): Path to granule NETCDF file

    Returns:
        list: List of beams
    """    
    netcdfdataset = Dataset(granule_netcdf)
    available_beams = [beam for beam in netcdfdataset.groups if beam in beamlist]
    return available_beams

def load_beam_array(filename, beam):
    """Generate a strucuted numpy array from a netcdf file for a given beam

    Args:
        filename (Pathlike): Path to netCDF file
        beam (str): beam name

    Returns:
        np.ndarray: numpy structured array of individual points 
    """        
    dimensions_dist = {
                "X" : f"{beam}/heights/lon_ph",
                "Y" : f"{beam}/heights/lat_ph",
                "Z" : f"{beam}/heights/h_ph",
                "tr_d":f"{beam}/heights/dist_ph_along",
                "time":f"{beam}/heights/delta_time",
            }
    pipelineobject = pdal.Reader.hdf(filename=atl03_testfile,dimensions=dimensions_dist).pipeline()
    try:
        pipelineobject.execute()
        return pipelineobject.arrays[0]
    except RuntimeError:
        print(f"Beam {beam} missing from {filename}")
        return None


def get_track_gdf(outarray):
    linegeom = get_track_geom(outarray)
    return gpd.GeoDataFrame(
        {"geometry": [linegeom]}, crs="EPSG:7912", geometry="geometry"
    )


def get_track_geom(outarray):
    if outarray is not None:
        coords = [
            [outarray["X"].min(), outarray["Y"].min()],
            [outarray["X"].max(), outarray["Y"].max()],
        ]
        # print(coords)
        return LineString(coords)
