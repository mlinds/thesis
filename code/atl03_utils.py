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
    SN1 = (np.pi * Ra**2 * N1) / (h * seglen / hscale)
    SN2 = (np.pi * Ra**2 * N2) / (h2 * seglen / hscale)
    # coerce into an int
    minpoints = int((2 * SN1 - SN2) / np.log((2 * SN1 / SN2)))
    # lowest it can return is 3
    print(f"{seglen=},{N1=},{N2=},{h=}")
    return max(minpoints, 3)


def get_beams(granule_netcdf):
    """List the beams available for a given granule

    Args:
        granule_netcdf (Pathlike): Path to granule NETCDF file

    Returns:
        list: List of beams
    """
    # print(granule_netcdf)
    try:
        with Dataset(granule_netcdf) as netcdfdataset:
            return [beam for beam in netcdfdataset.groups if beam in beamlist]
    # i  know pass in an except block is bad coding but i need to find a better way of handling this
    except AttributeError:
        pass


def load_beam_array_ncds(filename, beam):
    """
    returns an array of photon-level details for a given file and beam name. Granule-level metadata is also included with the array
    """
    ds = Dataset(filename)

    # get the beam metadata
    stdate = ds.groups["ancillary_data"].variables["data_start_utc"][:]
    enddate = ds.groups["ancillary_data"].variables["data_end_utc"][:]
    strgt = int(ds.groups["ancillary_data"].variables["start_rgt"][:])
    endrgt = int(ds.groups["ancillary_data"].variables["end_rgt"][:])
    granule_quality = int(
        ds.groups["quality_assessment"].variables["qa_granule_pass_fail"][:]
    )

    try:
        # get array-type data
        Y = ds.groups[beam].groups["heights"].variables["lat_ph"][:]
        X = ds.groups[beam].groups["heights"].variables["lon_ph"][:]
        Z = ds.groups[beam].groups["heights"].variables["h_ph"][:]
        # based on the data documentation, the dates are referenced to the 2018-01-01 so the
        # datetimes are shifted accordingly
        delta_time = ds.groups[beam].groups["heights"].variables["delta_time"][
            :
        ] + np.datetime64("2018-01-01T00:00:00.0000000").astype("<f8")
        ocean_sig = ds.groups[beam].groups["heights"].variables["signal_conf_ph"][:, 1]
        land_sig = ds.groups[beam].groups["heights"].variables["signal_conf_ph"][:, 0]

        dtype = np.dtype(
            [
                ("X", "<f8"),
                ("Y", "<f8"),
                ("Z", "<f8"),
                ("delta_time", "<M8[ns]"),
                ("oc_sig_conf", "<i4"),
                ("land_sig_conf", "<i4"),
            ],
            metadata={
                "st_date": stdate,
                "end_date": enddate,
                "QA_PF": granule_quality,
                "Start RGT": strgt,
                "End RGT": endrgt,
            },
        )
        return np.rec.array((X, Y, Z, delta_time, ocean_sig, land_sig), dtype=dtype)
    # u if we can't find a certain beam, just return None
    except KeyError:
        logger.debug(
            "Beam %s missing from %s",
            beam,
        )
        return None
    # gotta remember to close the dataset
    finally:
        ds.close()


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


def get_beam_data(h5file, beam):
    point_array = load_beam_array_ncds(h5file, beam)
    track_geom = get_track_geom(point_array)

    return (track_geom,)


def make_gdf_from_ncdf_files(directory):
    # TODO fix this unreadable function
    beamlist = []
    datelist = []
    rgtlist = []
    filenamelist = []
    geomlist = []
    for h5file in glob.iglob(directory):
        # TODO change to use pathlib to make this more readable

        filefriendlyname = str(h5file.split("/")[-1]).strip(".nc")

        # all list writes need to be inside this loop
        for beam in get_beams(h5file):
            # get the point array and make it into a linestring
            point_array = load_beam_array_ncds(h5file, beam)

            track_geom = get_track_geom(point_array)

            # write to all the lists
            # we can stack this into a multiindex later

            filenamelist.append(filefriendlyname)
            beamlist.append(beam)
            geomlist.append(track_geom)

            if point_array is None:
                rgtlist.append(np.NaN)
                datelist.append(np.NaN)
            else:
                rgt = point_array.dtype.metadata["Start RGT"]
                date = point_array.dtype.metadata["st_date"]
                rgtlist.append(rgt)
                datelist.append(date)

    df = gpd.GeoDataFrame(
        {
            "file": filenamelist,
            "geometry": geomlist,
            "Reference Ground Track": rgtlist,
            "date": datelist,
            "beam": beamlist,
        },
        crs = 'EPSG:7912',
        geometry='geometry'
    ).set_index(['file','beam'])
    return df
