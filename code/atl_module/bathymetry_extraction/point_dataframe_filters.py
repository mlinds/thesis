from pathlib import Path

import pandas as pd

# from atl_module.geospatial_utils.geospatial_functions import add_track_dist_meters
from atl_module.bathymetry_extraction.refraction_correction import correct_refr
from atl_module.geospatial_utils.raster_interaction import query_raster

p = Path(__file__).parents[3]


def add_msl_corrected_seafloor_elev(df_in):
    # dac_tide = (df_in.z_kde - df_in.sea_level_interp) + df_in.dac_corr + df_in.tide_ocean_corr
    dac_tide = df_in.z_kde - df_in.sea_level_interp
    return df_in.assign(sf_elev_MSL=dac_tide)


def filter_high_returns(df, max_geoid_high_z):
    """Remove returns above *level* which is an elevation in meters

    Args:
        df (pd.DataFrame): input dataframe
        level (int, optional): level above which to remove points. Defaults to 5.

    Returns:
        pd.DataFrame: output dataframe
    """
    # remove any points above 5m
    return df.loc[(df.Z_geoid < max_geoid_high_z)]


def filter_TEP_and_nonassoc(df):
    """Remove Transmitter Echo Path (TEP) photons

    Args:
        df (pd.DataFrame): Input dataframe

    Returns:
        pd.DataFrame: Output dataframe
    """
    # remove any transmitter Echo Path photons
    return df.loc[df.oc_sig_conf >= 0]


# TODO rewrite this to include NAs for non-high-confience photons
def add_sea_surface_level(df, max_sea_surf_elev, rolling_window=200):
    # take rolling median of signal points along track distance
    # sea_level = (
    #     df.loc[df.oc_sig_conf >= 4]["Z_geoid"].rolling(rolling_window, center=True).median()
    # )

    # sigma_sea_level = (
    #     df.loc[df.oc_sig_conf == 4]["Z_geoid"].rolling(rolling_window, center=True).std()
    # )
    # sea_level.name = "sea_level"
    # newgdf = df.merge(
    #     right=sea_level,
    #     how="left",
    #     left_index=True,
    #     right_index=True,
    #     validate="1:1",
    # ).merge(
    #     right=sigma_sea_level,
    #     how="left",
    #     left_index=True,
    #     right_index=True,
    #     validate="1:1",
    # )

    # interp_sea_surf_elev = (
    #     pd.Series(data=newgdf.sea_level.array, index=newgdf.delta_time.array)
    #     # pd.Series(data=newgdf.sea_level.array, index=newgdf.delta_time.array)
    #     .interpolate(method="index").to_numpy()
    # )

    # find the median sea level
    constant_sealevel = df.loc[df.oc_sig_conf >= 4]["Z_geoid"].median()
    # find the std deviation
    constant_sealevel_std = df.loc[df.oc_sig_conf >= 4]["Z_geoid"].std()
    sealevel_df = df.assign(
        sea_level_interp=constant_sealevel, sea_level_std_dev=constant_sealevel_std
    )

    sealevel_df = sealevel_df.loc[sealevel_df.sea_level_interp < max_sea_surf_elev]

    return sealevel_df.dropna()


def filter_low_points(df, filter_below_z):
    # drop any points with an uncorrected depth greater than a threshold
    return df.loc[df.Z_geoid > filter_below_z]


def filter_depth(df, filter_below_depth):
    # drop any points with an uncorrected depth greater than a threshold
    depth_series = df.Z_geoid - df.sea_level_interp
    return df.loc[(depth_series > filter_below_depth)]


def remove_surface_points(df, n=1, min_remove=1):
    # remove all points `n` standard deviations away from the sea level
    # its constant so just grab the first one
    sea_level_std_dev = df.sea_level_interp.mean()
    return df.loc[df.Z_geoid < df.sea_level_interp - max(n * sea_level_std_dev, min_remove)]


def add_gebco(df):
    # query the gebco ncdf file, add the relevant GEBCO height
    gebco_height = query_raster(
        df,
        p.joinpath("data/GEBCO/GEBCO_2021_sub_ice_topo.nc"),
    )
    # return the dataframe with the new column
    return df.assign(gebco_elev=gebco_height)


def filter_gebco(df: pd.DataFrame, low_limit: float, high_limit: float):
    # check for gebco height in the columns
    if "gebco_elev" not in df.columns:
        raise ValueError("Make sure to add the gebco elevation before running this function")
    # filter points based on gebco
    df = df[df.gebco_elev > low_limit]
    df = df[df.gebco_elev < high_limit]
    return df


def correct_for_refraction(df):
    # get horizotnal and vertical refraction correction factors
    xcorr, ycorr, zcorr = correct_refr(
        # this is the depth, the sea level is referenced to the geoid
        df.sea_level_interp - df.Z_geoid,
        pointing_vector_az=df.p_vec_az,
        pointing_vector_elev=df.p_vec_elev,
    )
    # apply these factors to the dataframe
    return df.assign(Z_refr=df.Z_geoid + zcorr, easting_corr=xcorr, northing_corr=ycorr)


def _counter(series_in, window_distance_meters):
    center_loc = series_in.index[int(len(series_in) / 2)]
    series_in = series_in[
        (series_in.index > center_loc - window_distance_meters / 2)
        & (series_in.index < center_loc + window_distance_meters / 2)
    ]
    return series_in.count()


def add_neighbor_count(df, window_distance_pts, window_distance_meters):
    countseries = df.Z_geoid.rolling(window=window_distance_pts, center=True).apply(
        lambda x: _counter(x, window_distance_meters=window_distance_meters)
    )
    df.loc[:, f"neighbors_within_{window_distance_meters}m"] = countseries
    return df
