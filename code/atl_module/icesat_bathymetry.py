from atl_module.kde_peaks_method import get_elev_at_max_density, AccumulateKDEs
import pandas as pd
from glob import iglob
from tqdm import tqdm
from multiprocessing import Pool
import numpy as np
from atl_module import point_dataframe_filters as dfilt
from atl_module import geospatial_functions as geofn
from atl_module.load_netcdf import get_beams, load_beam_array_ncds


def add_along_track_dist(pointdata):
    if isinstance(pointdata, pd.DataFrame):
        pointdata = pointdata.to_records()
    return geofn.add_track_dist_meters(pointdata)


def _filter_points(raw_photon_df: pd.DataFrame) -> pd.DataFrame:
    """Remove points outside of the gebco nearshore zone, points that are invalied, or to high

    Args:
        beamdata (np.ndarray): structed ndarray recieved from the beam parsing function

    Returns:
        pd.DataFrame: pandas dataframe including the along-track distance
    """
    filtered_photon_df = (
        raw_photon_df.pipe(dfilt.add_sea_surface_level)
        .pipe(dfilt.filter_low_points, filter_below_z=40)
        .pipe(dfilt.remove_surface_points)
        .pipe(dfilt.add_gebco)
        .pipe(dfilt.filter_gebco, low_limit=-50, high_limit=6)
        .pipe(dfilt.filter_high_returns)
        .pipe(dfilt.filter_TEP_and_nonassoc)
        .pipe(dfilt.correct_for_refraction)
    )
    # reset
    # filtered_photon_df["dist_or"] = (
    #     filtered_photon_df.dist_or - filtered_photon_df.dist_or.min()
    # )

    return filtered_photon_df


# def get_kde_bathymetry(df,threshold,window):
#     if df is None:
#         return None

#     accumulator = AccumulateKDEs()
#     series_out = df.Z_g.rolling(window=window, center=True).apply(
#         accumulator.calc_kdeval_and_zval, raw=True, kwargs={"threshold": threshold}
#     )

#     df = df.assign(kde_seafloor=kde_elev,kernel_density=kd)
#     points_with_bathy = df[df.kde_seafloor.notna()]

#     return points_with_bathy


def add_rolling_kde(df, window):
    # set up the object to keep all the return values
    accumulator = AccumulateKDEs()
    # this series is a key to matching the KDE value and the Z elevation of the Max KDE to the points in original df
    # this is a complicated series of joins but it should support matching any arbitrary indexes
    series_out = (
        # apply the function from the object
        df.Z_g.rolling(window=window, center=True)
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


def get_all_bathy_from_granule(filename):
    # find which beams are available in the netcdf file
    beamlist = get_beams(filename)
    granulelist = []
    for beam in beamlist:
        # get numpy array of the beam data
        beamarray = load_beam_array_ncds(filename=filename, beam=beam)
        # convert numpy array to a geodataframe with the along-track distance
        point_df = geofn.add_track_dist_meters(beamarray)
        # filter out points could not be bathymetry
        filtered_df = _filter_points(point_df)
        bathy_pts = add_rolling_kde(filtered_df, window=200)
        thresholdval = bathy_pts.kde_val.mean() - 1 * bathy_pts.kde_val.std()
        bathy_pts = bathy_pts.loc[bathy_pts.kde_val > thresholdval]
        if len(bathy_pts) > 0:
            granulelist.append(bathy_pts)
    if len(granulelist) > 0:
        return pd.concat(granulelist)


def bathy_from_all_tracks(path):
    dflist = []
    for filename in tqdm(iglob(path + "/ATL03/*.nc")):
        dflist.append(get_all_bathy_from_granule(filename))
    return pd.concat(dflist)


def bathy_from_all_tracks_parallel(folderpath):
    filenamelist = list(iglob(folderpath + "/ATL03/*.nc"))
    with Pool() as pool:
        result = pool.map(get_all_bathy_from_granule, filenamelist)
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
