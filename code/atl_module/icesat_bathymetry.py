from atl_module.kde_peaks_method import get_elev_at_max_density, AccumulateKDEs
import pandas as pd
from glob import iglob
from tqdm import tqdm
from multiprocessing import Pool
import numpy as np
from atl_module import point_dataframe_filters as dfilt
from atl_module import geospatial_functions as geofn
from atl_module.load_netcdf import get_beams, load_beam_array_ncds
import itertools


def add_along_track_dist(pointdata):
    if isinstance(pointdata, pd.DataFrame):
        pointdata = pointdata.to_records()
    return geofn.add_track_dist_meters(pointdata)


def _filter_points(raw_photon_df: pd.DataFrame) -> pd.DataFrame:
    """Remove points outside of the gebco nearshore zone, points that are invalied, or too high. Also calculate refraction corrections and add them to the dataframe

    Args:
        beamdata (np.ndarray): structed ndarray recieved from the beam parsing function

    Returns:
        pd.DataFrame: pandas dataframe including the along-track distance
    """
    filtered_photon_df = (
        raw_photon_df.pipe(dfilt.add_gebco)
<<<<<<< HEAD
        .pipe(dfilt.filter_gebco, low_limit=-40, high_limit=2)
=======
        .pipe(dfilt.filter_gebco, low_limit=-50, high_limit=6)
>>>>>>> d54fd8667c869c15d20e6279a500c90ed38c029e
        .pipe(dfilt.add_sea_surface_level)
        .pipe(dfilt.filter_low_points, filter_below_z=40)
        .pipe(dfilt.remove_surface_points, n=1)
        .pipe(dfilt.filter_high_returns)
        .pipe(dfilt.filter_TEP_and_nonassoc)
        .pipe(dfilt.correct_for_refraction)
    )
    # reset the distances be zero at the first photon
    # commenting out for now since not needed and makes comparison harder

    # filtered_photon_df["dist_or"] = (
    #     filtered_photon_df.dist_or - filtered_photon_df.dist_or.min()
    # )

    return filtered_photon_df


def add_rolling_kde(df, window):
    # set up the object to keep all the return values
    accumulator = AccumulateKDEs()
    # this series is a key to matching the KDE value and the Z elevation of the Max KDE to the points in original df
    # this is a complicated series of joins but it should support matching any arbitrary indexes
    series_out = (
        # apply the function from the object
        df.Z_refr.rolling(window=window, center=True)
        .apply(accumulator.calc_kdeval_and_zval, raw=True)
        .dropna()
        .astype("int")
    )
    # rename the series so the merge works
    series_out.name = "matchup"
    kdevals_df = pd.DataFrame(accumulator.returndict).set_index("matchup")
    merge_df = (
        pd.DataFrame(series_out)
        .merge(kdevals_df, left_on="matchup", right_index=True)
        .drop(columns="matchup")
    )
    df_w_kde = df.merge(merge_df, right_index=True, left_index=True, how="left")
    # make sure we didn't lose anything
    assert (
        df_w_kde.shape[0] == df.shape[0]
    ), "rolling KDE was not added correctly for all points"
    return df_w_kde


def get_all_bathy_from_granule(filename, window, threshold_val, req_perc_hconf):
    """For a single granule (stored in a netcdf4 file), loop over ever single beam, determine if it contains useful bathymetry signal, and return a dataframe just of the bathymetric points

    Args:
        filename (str or PathLike): location of the NetCDF4 file
        window (int): The length, in *number of points* of the rolling window function
        threshold_val (float): cutoff value of kerndel density for a point to be consider a signal point, in  number of standard deviations away from the median kernel density
        req_perc_hconf (float): Minimum percentage of high confidence ocean photons in a granule for the granule to be included

    Returns:
        pd.DataFrame: Pandas Dataframe of bathymetric points
    """
    # find which beams are available in the netcdf file
    beamlist = get_beams(filename)
    granulelist = []
    for beam in beamlist:
        # get numpy array of the beam data
        beamarray = load_beam_array_ncds(filename=filename, beam=beam)
        # get the metadata dictionary
        metadata_dict = beamarray.dtype.metadata
        # the percentage of high confidence ocean photons is a proxy for the overall quality of the signal
        if metadata_dict["ocean_high_conf_perc"] < req_perc_hconf:
            continue
        # convert numpy array to a geodataframe with the along-track distance
        point_df = geofn.add_track_dist_meters(beamarray)
        # get df of points in the subsurface region (ie. filter out points could not be bathymetry)
        subsurface_return_pts = _filter_points(point_df)

        bathy_pts = add_rolling_kde(subsurface_return_pts, window=window)
        thresholdval = (
            bathy_pts.kde_val.mean() - threshold_val * bathy_pts.kde_val.std()
        )
        bathy_pts = bathy_pts.loc[bathy_pts.kde_val > thresholdval]
        bathy_pts = bathy_pts.assign(
            atm_profile=metadata_dict["atmosphere_profile"],
            beamtype=metadata_dict["atlas_beam_type"],
            oc_hconf_perc=metadata_dict["ocean_high_conf_perc"],
        )
        # catch the case where there is no signal in one beam
        if len(bathy_pts) > 0:
            granulelist.append(bathy_pts)
    # catch the case where there is no signal in any beams in the granule
    if len(granulelist) > 0:
        return pd.concat(granulelist)


def bathy_from_all_tracks(path):
    dflist = []
    for filename in tqdm(iglob(path + "/ATL03/*.nc")):
        dflist.append(get_all_bathy_from_granule(filename))
    return pd.concat(dflist)


def bathy_from_all_tracks_parallel(folderpath, window, threshold_val, req_perc_hconf):
    """Run the kde function for every single granule in parallel

    Args:
        folderpath (str): Path to directory where the netcdf files are stored
        window (int): The number of points to use in the windowing function
        threshold_val (float): the *number of standard deviation* away from the median to include. If 0, only include points greater than the median value
        req_perc_hconf (float): Minimum percent of high confidence ocean points to include the granule in the data at all

    Returns:
        GeoDataFrame: Geodataframe of the locations of photons that are bathmetry
    """

    # to run the algorithm for all granules in parallel, create an iterable of tuples with the function parameters (as required by pool.starmap)
    # TODO jesus this is unreadable, there must be a better way to make this iterator.
    # maybe go back to map, and feed map object the a modified function with lambda or functools.partial
    filenamelist = list(
        zip(
            iglob(folderpath + "/ATL03/*.nc"),
            itertools.repeat(window),
            itertools.repeat(threshold_val),
            itertools.repeat(req_perc_hconf),
        )
    )
    with Pool() as pool:
        result = pool.starmap(get_all_bathy_from_granule, filenamelist)
    if len(result) > 1:
        return pd.concat(result)
    elif len(result) == 1:
        return result


def run_multiple(paths):

    for path in paths:
        print("starting folder", path)
        outpath = path + "/all_bathy_pts.gpkg"
        combined_result = bathy_from_all_tracks_parallel(path)
        combined_result.to_file(outpath)
        print("wrote results to ", outpath)
