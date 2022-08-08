import itertools
from glob import iglob
from multiprocessing import Pool

import pandas as pd
from atl_module.bathymetry_extraction import point_dataframe_filters as dfilt
from atl_module.bathymetry_extraction.kde_peaks_method import AccumulateKDEs
from atl_module.geospatial_utils import geospatial_functions as geofn
from atl_module.io.atl03_netcdf_loading import get_beams, load_beam_array_ncds
from logzero import setup_logger
from tqdm import tqdm

# TODO try thread based parallelism with:
# from multiprocessing.dummy import Pool


detail_logger = setup_logger(name="details")


def add_along_track_dist(pointdata):
    if isinstance(pointdata, pd.DataFrame):
        pointdata = pointdata.to_records()
    return geofn.add_track_dist_meters(pointdata)


def _filter_points(
    raw_photon_df: pd.DataFrame,
    low_limit,
    high_limit,
    rolling_window,
    max_sea_surf_elev,
    filter_below_z,
    filter_below_depth,
    n,
    max_geoid_high_z,
) -> pd.DataFrame:
    """Remove points outside of the gebco nearshore zone, points that are invalied, or too high. Also calculate refraction corrections and add them to the dataframe

    Args:
        beamdata (np.ndarray): structed ndarray recieved from the beam parsing function

    Returns:
        pd.DataFrame: pandas dataframe including the along-track distance
    """
    filtered_photon_df = (
        raw_photon_df.pipe(dfilt.add_gebco)
        .pipe(dfilt.filter_gebco, low_limit=low_limit, high_limit=high_limit)
        .pipe(
            dfilt.add_sea_surface_level,
            rolling_window=rolling_window,
            max_sea_surf_elev=max_sea_surf_elev,
        )
        .pipe(dfilt.filter_low_points, filter_below_z=filter_below_z)
        .pipe(dfilt.filter_depth, filter_below_depth=filter_below_depth)
        .pipe(dfilt.remove_surface_points, n=n)
        .pipe(dfilt.filter_high_returns, max_geoid_high_z=max_geoid_high_z)
        .pipe(dfilt.filter_TEP_and_nonassoc)
        .pipe(dfilt.correct_for_refraction)
        # .pipe(dfilt.add_neigbor_count, window_distance_pts=200,window_distance_meters=200)
    )
    return filtered_photon_df


def add_rolling_kde(df, window, window_meters, min_photons):
    # set up the object to keep all the return values
    accumulator = AccumulateKDEs(window_meters=window_meters, min_photons=min_photons)
    # this series is a key to matching the KDE value and the Z elevation of the Max KDE to the points in original df
    # this is a complicated series of joins but it should support matching any arbitrary indexes
    series_out = (
        # apply the function from the object
        df.Z_refr.rolling(window=window, center=True)
        .apply(
            accumulator.calc_kdeval_and_zval,
        )
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


def get_all_bathy_from_granule(
    filename,
    window,
    threshold_val,
    req_perc_hconf,
    window_meters,
    min_photons,
    min_kde,
    low_limit,
    high_limit,
    rolling_window,
    max_sea_surf_elev,
    filter_below_z,
    filter_below_depth,
    n,
    max_geoid_high_z,
):
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
            # go to the next one of the quality isn't high enough
            continue
        # convert numpy array to a geodataframe with the along-track distance
        # point_df = geofn.add_track_dist_meters(beamarray)
        point_df = pd.DataFrame(beamarray)
        # get df of points in the subsurface region (ie. filter out points could not be bathymetry)
        subsurface_return_pts = _filter_points(
            point_df,
            low_limit,
            high_limit,
            rolling_window,
            max_sea_surf_elev,
            filter_below_z,
            filter_below_depth,
            n,
            max_geoid_high_z,
        )
        # find the bathymetry points using the KDE function
        bathy_pts = add_rolling_kde(
            subsurface_return_pts,
            window=window,
            min_photons=min_photons,
            window_meters=window_meters,
        )
        # find the minimum KDE strength
        thresholdval = bathy_pts.kde_val.mean() - threshold_val * bathy_pts.kde_val.std()
        # find the
        bathy_pts = bathy_pts.loc[bathy_pts.kde_val > max(thresholdval, min_kde)]
        # TODO could this be assigned to another function? not directly related to this function
        bathy_pts = bathy_pts.assign(
            beam=metadata_dict["beam"],
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


def bathy_from_all_tracks(
    folderpath,
    window,
    threshold_val,
    req_perc_hconf,
    window_meters,
    min_photons,
    min_kde,
):
    dflist = []
    for filename in tqdm(iglob(folderpath + "/ATL03/*.nc")):
        dflist.append(
            get_all_bathy_from_granule(
                filename,
                window,
                threshold_val,
                req_perc_hconf,
                window_meters,
                min_photons,
            )
        )
    return pd.concat(dflist)


def bathy_from_all_tracks_parallel(
    folderpath,
    window,
    threshold_val,
    req_perc_hconf,
    window_meters,
    min_photons,
    min_kde,
    low_limit,
    high_limit,
    rolling_window,
    max_sea_surf_elev,
    filter_below_z,
    filter_below_depth,
    n,
    max_geoid_high_z,
):
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
            itertools.repeat(window_meters),
            itertools.repeat(min_photons),
            itertools.repeat(min_kde),
            itertools.repeat(low_limit),
            itertools.repeat(high_limit),
            itertools.repeat(rolling_window),
            itertools.repeat(max_sea_surf_elev),
            itertools.repeat(filter_below_z),
            itertools.repeat(filter_below_depth),
            itertools.repeat(n),
            itertools.repeat(max_geoid_high_z),
        )
    )

    with Pool() as pool:
        result = pool.starmap(get_all_bathy_from_granule, filenamelist)
    # catch the case where there is no bathymetry found in the granule
    if len(result) > 1:
        return pd.concat(result)
    # catch the case where there is only one, so no concatenation is required
    elif len(result) == 1:
        return result
