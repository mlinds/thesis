import geopandas as gpd
import numpy as np

# import pdal
from netCDF4 import Dataset
from shapely.geometry import LineString
import glob
import pandas as pd
import logging

beamlist = ["gt1l", "gt1r", "gt2l", "gt2r", "gt3l", "gt3r"]

logger = logging.getLogger("ATL03_Data_cleaning")

# i'm super lazy and just made this to autocomplete the beam names when typing


class Beams:
    gt1l = "gt1l"
    gt1r = "gt1r"
    gt2l = "gt2l"
    gt2r = "gt2r"
    gt3l = "gt3l"
    gt3r = "gt3r"


def min_dbscan_points(oned_pt_array_in, Ra, hscale):
    """Get the minimmum points parameter for DBSCAN as defined in Ma et al 2021
    Args:
        oned_pt_array_in (np.array): Numpy Structured array from PDAL pipeline

    Returns:
        float: The minimum cluster size for DBSCAN
    """
    h2 = 5
    N1 = oned_pt_array_in.shape[0]
    h = oned_pt_array_in["Z"].max() - oned_pt_array_in["Z"].min()
    seglen = oned_pt_array_in["dist_or"].max() - oned_pt_array_in["dist_or"].min()
    # find the boundary for the lowest 5m
    zlim = oned_pt_array_in["Z"].min() + h2
    # anything below that gets counted as above
    N2 = oned_pt_array_in["Z"][oned_pt_array_in["Z"] < zlim].shape[0]
    SN1 = (np.pi * Ra ** 2 * N1) / (h * seglen / hscale)
    SN2 = (np.pi * Ra ** 2 * N2) / (h2 * seglen / hscale)
    # coerce into an int
    minpoints = int((2 * SN1 - SN2) / np.log((2 * SN1 / SN2)))
    # lowest it can return is 3
    print(f"{seglen=},{N1=},{N2=},{h=}")
    return max(minpoints, 5)


def get_beams(granule_netcdf):
    """List the beams available for a given granule

    Args:
        granule_netcdf (Pathlike): Path to granule NETCDF file

    Returns:
        list: List of beams
    """
    netcdfdataset = Dataset(granule_netcdf)

    return [beam for beam in netcdfdataset.groups if beam in beamlist]


def load_beam_array_ncds(filename, beam):
    """
    Updated implementiation of the load_beam_array function which uses netCDF4 library instead of PDAL.
    about 20% faster than PDAL so I need to change the API to only use this/
    """
    try:
        ds = Dataset(filename)
        Y = ds.groups[beam].groups["heights"].variables["lat_ph"][:]
        X = ds.groups[beam].groups["heights"].variables["lon_ph"][:]
        Z = ds.groups[beam].groups["heights"].variables["h_ph"][:]
        date = ds.getncattr("time_coverage_start")
        dtype = np.dtype(
            [("X", "<f8"), ("Y", "<f8"), ("Z", "<f8")], metadata={"st_date": date}
        )
        return np.rec.array((X, Y, Z), dtype=dtype)
    except KeyError:
        logger.debug(
            "Beam %s missing from %s",
            beam,
        )
        return None


# speedtest this vs other netcdf
def load_beam_array(filename, beam):
    """Generate a structured numpy array from a netcdf file for a given beam

    Args:
        filename (Pathlike): Path to netCDF file
        beam (str): beam name

    Returns:
        np.ndarray: numpy structured array of individual points
    """
    dimensions_dist = {
        "X": f"{beam}/heights/lon_ph",
        "Y": f"{beam}/heights/lat_ph",
        "Z": f"{beam}/heights/h_ph",
        "tr_d": f"{beam}/heights/dist_ph_along",
        # "time":f"{beam}/heights/delta_time",
    }
    pipelineobject = pdal.Reader.hdf(
        filename=filename, dimensions=dimensions_dist
    ).pipeline()
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
        ymin = outarray["Y"].min()
        xmin = outarray["X"][outarray["Y"].argmin()]
        ymax = outarray["Y"].max()
        xmax = outarray["X"][outarray["Y"].argmax()]
        coords = [
            [xmin, ymin],
            [xmax, ymax],
        ]
        # print(coords)
        return LineString(coords)


def read_ncdf(inpfile):
    beams_available_file = get_beams(inpfile)
    beamcoords = {}
    for beam in beams_available_file:
        array = load_beam_array_ncds(inpfile, beam)
        beamcoords[beam] = get_track_geom(array)
        yield array


def make_gdf_from_ncdf_files(directory):
    outdict = {}
    for h5file in glob.iglob(directory):
        beamdict = {}
        filefriendlyname = str(h5file.split("/")[3]).strip(".h5")
        for beam in get_beams(h5file):
            # print(f"getting {beam} from {h5file}")
            point_array = load_beam_array_ncds(h5file, beam)
            track_geom = get_track_geom(point_array)
            beamdict[beam] = track_geom

        outdict[filefriendlyname] = beamdict
        # st_rgt = Dataset(h5file).groups['ancilliary_data'].variables['start_rgt'][:]

    innerdf = pd.DataFrame.from_dict(outdict, orient="index").stack()
    trackgdf = (
        gpd.GeoDataFrame(innerdf, crs="EPSG:7912")
        .rename(columns={0: "geometry"})
        .set_geometry("geometry")
    )
    return trackgdf
