"""
TODO:
- GEBCO automatic download function

"""
import glob
import logging
from math import ceil
from os import PathLike
from os.path import basename
from subprocess import PIPE, Popen
from sklearn.metrics import mean_squared_error

import geopandas as gpd
import numpy as np
import pandas as pd
from cftime import num2pydate
from netCDF4 import Dataset
from pandas.api.extensions import register_dataframe_accessor
from shapely.geometry import LineString, Point
from sklearn.cluster import DBSCAN


np.seterr(all="warn")

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


def min_dbscan_points(oned_pt_array_in: np.array, Ra: float, hscale: float) -> int:
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


def get_beams(granule_netcdf: str or PathLike) -> list:
    """List the beams available for a given granule

    Args:
        granule_netcdf (Pathlike): Path to granule NETCDF file

    Returns:
        list: List of beams
    """
    try:
        with Dataset(granule_netcdf) as netcdfdataset:
            return [
                beam
                for beam in netcdfdataset.groups
                if (beam in beamlist)
                and ("heights" in netcdfdataset.groups[beam].groups)
            ]
    # i  know pass in an except block is bad coding but i need to find a better way of handling this
    except AttributeError:
        pass


def load_beam_array_ncds(filename: str or PathLike, beam: str) -> np.ndarray:
    """return an array of photon-level details for a given file and beam name.

    Granule-level metadata is also included with the array
    """
    # this function is a mess and should probably abstracted into smaller functions
    # if the pandas df induces too much overhead, could maybe be rewritten in numpy

    with Dataset(filename) as ds:

        # get the granule-level metadata
        metadata = {
            varname: str(values[:])
            for varname, values in ds.groups["ancillary_data"].variables.items()
        }
        # add the beam-level metadata by looping over attribute names and getting them from the
        # netcdf group
        for attribute_name in ds.groups[beam].ncattrs():
            metadata[attribute_name] = str(getattr(ds.groups[beam], attribute_name))

        try:
            metadata["ocean_high_conf_perc"] = float(
                ds.groups["quality_assessment"]
                .groups[beam]
                .variables["qa_perc_signal_conf_ph_high"][:, 1]
            )
        except KeyError:
            metadata["ocean_high_conf_perc"] = np.NaN

        # this is in a try block because it raises a keyerror if the beam is missing from the granule
        try:
            ds.groups[beam].groups["heights"]

        except KeyError:
            logger.debug(
                "Beam %s missing from %s",
                beam,
            )
            return None
        # get array-type data
        Y = ds.groups[beam].groups["heights"].variables["lat_ph"][:]
        X = ds.groups[beam].groups["heights"].variables["lon_ph"][:]
        Z = ds.groups[beam].groups["heights"].variables["h_ph"][:]

        # based on the data documentation, the dates are referenced to the 2018-01-01 so the
        # datetimes are shifted accordingly
        delta_time_s = ds.groups[beam].groups["heights"].variables["delta_time"][:]
        delta_time = num2pydate(delta_time_s, "seconds since 2018-01-01")

        ocean_sig = ds.groups[beam].groups["heights"].variables["signal_conf_ph"][:, 1]
        land_sig = ds.groups[beam].groups["heights"].variables["signal_conf_ph"][:, 0]

        # need to deal with geophysical variable time differenently since they're captured at a different rate
        delta_time_geophys_s = (
            ds.groups[beam].groups["geophys_corr"].variables["delta_time"][:]
        )
        delta_time_geophys = num2pydate(
            delta_time_geophys_s, "seconds since 2018-01-01"
        )

        # to index these we need to set the first value to the first value of the
        # photon returns. This is because the photon time values start in the middle of a segment

        delta_time_geophys[0] = delta_time[0]

        # get the geophysical variables
        geo_f2m = (
            ds.groups[beam]
            .groups["geophys_corr"]
            .variables["geoid_free2mean"][:]
            .filled(np.NaN)
        )
        geoid = (
            ds.groups[beam].groups["geophys_corr"].variables["geoid"][:].filled(np.NaN)
        )
        tide_ocean = (
            ds.groups[beam]
            .groups["geophys_corr"]
            .variables["tide_ocean"][:]
            .filled(np.NaN)
        )

        # combine the corrections into one
        # this must be subtracted from Z ellipsoidal (see page 3 of data comparison manual v005)
        correction = geoid + geo_f2m + tide_ocean

        # to assign the correct correction value, we need to get the correction at a certain time
        # to do this we can align them using the pandas asof

        # switch into pandas to use as_of function
        zcorr_series = pd.Series(correction, index=delta_time_geophys).sort_index()

        # make an array of the correction by time
        z_corr = zcorr_series.asof(delta_time).to_numpy()

        # get the corrected Z vals
        Z_corrected = Z - z_corr

        # for varname, values in (
        #     ds.groups["quality_assessment"].groups[beam].variables.items()
        # ):
        #     metadata[varname + "_ocean"] = values[:].data[0][1]
        #     metadata[varname + "_land"] = values[:].data[0][0]

        # creating a structured array

        dtype = np.dtype(
            [
                ("X", "<f8"),
                ("Y", "<f8"),
                ("Z", "<f8"),
                ("Z_g", "<f8"),
                ("delta_time", "<M8[ns]"),
                ("oc_sig_conf", "<i4"),
                ("land_sig_conf", "<i4"),
            ],
            metadata=metadata,
        )

        # then we assign each 1darray to the structured array
        photon_data = np.empty(len(X), dtype=dtype)
        photon_data["X"] = X
        photon_data["Y"] = Y
        photon_data["Z"] = Z
        photon_data["Z_g"] = Z_corrected
        photon_data["delta_time"] = delta_time
        photon_data["oc_sig_conf"] = ocean_sig
        photon_data["land_sig_conf"] = land_sig

        return photon_data


def get_track_gdf(outarray: np.ndarray) -> gpd.GeoDataFrame:
    """Create a geodataframe for a track as defined by an array of photon returns

    Args:
        outarray (np.ndarray): structured array of photon locations

    Returns:
        gpd.GeoDataFrame: A geodataframe of a particular track
    """
    linegeom = get_track_geom(outarray)
    return gpd.GeoDataFrame(
        {"geometry": [linegeom]}, crs="EPSG:7912", geometry="geometry"
    )


def get_track_geom(beamarray: np.ndarray) -> LineString:
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
    # TODO fix this unreadable function
    # try to decrease the indent level - itertools?
    beamlist = []
    datelist = []
    rgtlist = []
    filenamelist = []
    geomlist = []
    beam_type_list = []
    # percent_high_conf = []
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
        crs="EPSG:7912",
        geometry="geometry",
    ).set_index(["file", "beam"])

    # prooject it to the appropriate UTM system
    crs_UTM = gdf.estimate_utm_crs()
    gdf.to_crs(crs_UTM, inplace=True)
    return gdf


def add_track_dist_meters(
    # y is lat, x is lon
    strctarray,
    geodataframe=False,
) -> pd.DataFrame or gpd.GeoDataFrame:
    xcoords = strctarray["X"]
    ycoords = strctarray["Y"]
    # geom = [Point((x, y)) for x, y in zip(xcoords, ycoords)]
    geom = gpd.points_from_xy(xcoords, ycoords, crs="EPSG:7912")
    gdf = gpd.GeoDataFrame(strctarray, geometry=geom, crs="EPSG:7912")
    # to find distance in meters we need to estimate the UTM zone required
    utmzone = gdf.estimate_utm_crs()
    # convert to the UTM zone we found
    gdf = gdf.to_crs(utmzone)
    ymin = gdf.geometry.y.min()
    xmin = gdf.geometry.x[gdf.geometry.y.argmin()]

    dist = gdf.distance(Point(xmin, ymin))

    gdf = gdf.assign(dist_or=dist).sort_values("dist_or")
    # return a dataframe
    return gdf if geodataframe else pd.DataFrame(gdf.drop(columns="geometry"))


def _assign_na_values(inpval):
    """
    assign the appropriate value to the output of the gdallocationinfo response. '-99999' and an empty string are NaN values

    Anything else will return the input coerced to a float
    """
    return np.NaN if inpval in ["", "-999999"] else float(inpval)


# function that gets values from rasters for each lidar photon
def query_raster(dataframe, src):
    # takes a dataframe of points, and any GDAL raster as input
    xylist = dataframe.loc[:, ["X", "Y"]].values
    # take x,y pairs from dataframe, convert to a big string, then into a bytestring to feed into the pipe

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


@register_dataframe_accessor("bathy")
class TransectFixer:
    def __init__(self, dataframe):
        self._validate(dataframe)
        self._df = dataframe

    @staticmethod
    def _validate(dataframe):
        pass

    def filter_high_returns(self, level=5):
        # remove any points above 5m
        return self._df.loc[(self._df.Z_g < 5)]

    def filter_TEP(self):
        return self._df.loc[self._df.oc_sig_conf != -2]

    def add_sea_level(self, rolling_window=50):
        # take rolling median of signal points along track distance
        sea_level = (
            self._df.loc[self._df.oc_sig_conf >= 4]["Z_g"]
            .rolling(
                rolling_window,
            )
            .median()
        )

        sigma_sea_level = (
            self._df.loc[self._df.oc_sig_conf == 4]["Z_g"]
            .rolling(
                rolling_window,
            )
            .std()
        )
        sea_level.name = "sea_level"

        newgdf = self._df.merge(
            right=sea_level,
            how="left",
            left_index=True,
            right_index=True,
            validate="1:1",
        ).merge(
            right=sigma_sea_level,
            how="left",
            left_index=True,
            right_index=True,
            validate="1:1",
        )

        return self._df.assign(
            sea_level_interp=pd.Series(
                data=newgdf.sea_level.array, index=newgdf.dist_or.array
            )
            .interpolate(method="index")
            .to_numpy(),
            # sea_level_std_dev=pd.Series(
            #     data=newgdf.sea_level.array, index=newgdf.dist_or.array
            # ),
        ).dropna()

    def filter_low_points(self):
        # drop any points with an uncorrected depth greater than 50m

        return self._df.loc[self._df.sea_level_interp - self._df.Z_g < 50]

    def remove_surface_points(self, n=3, min_remove=1):
        sea_level_std_dev = self._df.sea_level_interp.std()
        return self._df.loc[
            self._df.Z_g
            < self._df.sea_level_interp - max(n * sea_level_std_dev, min_remove)
        ]

    def add_gebco(self):
        # query the gebco ncdf file, add the relevant GEBCO height
        gebco_height = query_raster(
            self._df,
            "../data/GEBCO/GEBCO_2021_sub_ice_topo.nc",
        )
        # return the dataframe with the new column
        return self._df.assign(gebco_elev=gebco_height)


def cluster_signal_dbscan(
    beam_df: pd.DataFrame, minpts=3, chunksize=500, Ra=0.1, hscale=1
):
    # create emtpy list to store the chunks
    sndf = []
    total_length = beam_df.dist_or.max()
    nchunks = ceil(total_length / chunksize)
    dist_st = 0
    # find the edges of the bins in meters
    bin_edges = list(
        zip(
            range(0, (nchunks - 1) * chunksize, chunksize),
            range(chunksize, nchunks * chunksize, chunksize),
        )
    )

    # loop over the bins and classify
    for dist_st, dist_end in bin_edges:
        array = beam_df.loc[
            (beam_df.dist_or > dist_st) & (beam_df.dist_or < dist_end)
        ].to_records()
        if len(array) < 10:
            continue

        V = np.linalg.inv(np.cov(array["dist_or"] / hscale, array["Z"]))
        fitarray = np.stack([array["dist_or"] / hscale, array["Z"]]).transpose()

        # run the clustering algo on the section
        clustering = DBSCAN(
            eps=Ra,
            # max_eps=Ra,
            min_samples=minpts,
            metric="mahalanobis",
            metric_params={"VI": V},
            # cluster_method='dbscan'
        ).fit(fitarray)
        df = pd.DataFrame(array).assign(cluster=clustering.labels_)

        df.loc[:, "SN"] = df.cluster.apply(lambda x: "noise" if x == -1 else "signal")
        sndf.append(df)

    merged = pd.concat(
        sndf,
    )

    return merged


def add_raw_seafloor(beam_df: pd.DataFrame):
    signal_pts = beam_df.loc[beam_df.SN == "signal"]

    signal_pts = signal_pts.assign(seafloor=signal_pts.Z_g.rolling(100).median())
    signal_pts = signal_pts.assign(
        depth=signal_pts.sea_level_interp - signal_pts.seafloor
    )
    signal_pts = signal_pts.assign(sf_refr=signal_pts.Z_g + 0.2541 * signal_pts.depth)

    return signal_pts


def add_dem_data(beam_df: pd.DataFrame, demlist: list) -> pd.DataFrame:

    for dempath in demlist:
        demname = basename(dempath).split(".")[0]
        values_at_pt = query_raster(beam_df, dempath)
        beam_df.loc[:, (demname)] = values_at_pt

    return beam_df


def calc_rms_error(beam_df, column_names: list):
    error_dict = {}
    # go over the each DEM, and find the RMS error with the calculated seafloor
    for column in column_names:
        # get a subset of the dataframe that is the seafloor and the column of interest
        comp_columns = beam_df.loc[:, ["sf_refr", column]].dropna()
        if len(comp_columns) == 0:
            error_dict[str(column) + "_error"] = np.NaN
        else:
            rms_error = mean_squared_error(
                comp_columns.loc[:, column], comp_columns.loc[:, "sf_refr"]
            )
            error_dict[str(column) + "_error"] = rms_error

    return error_dict
