# %%
import atl03_utils
from kde_peaks_method import get_elev_at_max_density
import pandas as pd
from glob import iglob
from tqdm import tqdm
from multiprocessing import Pool
import numpy as np


def _interpolate_dataframe(
    point_dataframe: pd.DataFrame, spacing: float
) -> pd.DataFrame:
    """Adds regularly-spaced horizontal points that can then be interpolated to fill the NA values

    Args:
        point_dataframe (pd.DataFrame): Dataframe of photon returns
        spacing (float): The distance to add the extra points in meters

    Returns:
        pd.DataFrame: Dataframe with the old points, plus the added regularly-spaced NA values
    """

    # make a new df with the distance as the index
    interpdf = point_dataframe.set_index("dist_or")
    # create a new index with a point every 10 m
    xindex_interp = np.arange(interpdf.index.min(), interpdf.index.max(), spacing)
    # the new index is the combo of the 10m index with the old index
    newindex = interpdf.index.union(xindex_interp)
    # set the new index and return the dataframe
    return interpdf.reindex(newindex)


def _filter_points(beamdata: np.ndarray) -> pd.DataFrame:
    """Remove points outside of the gebco nearshore zone, points that are invalied, or to high

    Args:
        beamdata (np.ndarray): structed ndarray recieved from the beam parsing function

    Returns:
        pd.DataFrame: pandas dataframe including the along-track distance
    """
    point_dataframe = pd.DataFrame(beamdata)
    point_dataframe = _filter_gebco(point_dataframe, -50, 2)
    point_dataframe = point_dataframe.bathy.filter_high_returns()
    point_dataframe = point_dataframe.bathy.filter_TEP()

    point_dataframe = atl03_utils.add_track_dist_meters(
        point_dataframe, geodataframe=True
    )
    point_dataframe = point_dataframe.bathy.add_sea_level()
    point_dataframe = point_dataframe.bathy.filter_low_points()
    point_dataframe = point_dataframe.bathy.remove_surface_points(n=3)
    # Recalculate the horizontal distance
    point_dataframe["dist_or"] = point_dataframe.dist_or - point_dataframe.dist_or.min()

    return point_dataframe


def _filter_gebco(df: pd.DataFrame, low_limit: float, high_limit: float):
    # add the gebco points
    df = df.bathy.add_gebco()
    # filter points based on gebco
    df = df[df.gebco_elev > -50]
    df = df[df.gebco_elev < 2]
    return df


def _apply_kde(point_dataframe):

    kde_elev = point_dataframe.Z_g.rolling(window=200, center=True).apply(
        get_elev_at_max_density, raw=True, kwargs={"threshold": 0.07}
    )

    point_dataframe = point_dataframe.assign(kde_seafloor=kde_elev)
    points_with_bathy = point_dataframe[point_dataframe.kde_seafloor.notna()]

    return points_with_bathy


def get_all_bathy_from_granule(filename):
    # find which beams are available in the netcdf file\
    beamlist = atl03_utils.get_beams(filename)
    granulelist = []
    for beam in beamlist:
        bathy_pts = _apply_kde(_filter_points(filename, beam))
        print(len(bathy_pts), "Points with bathymetry found")
        if len(bathy_pts) > 0:
            granulelist.append(bathy_pts)
    # print(granulelist)
    if len(granulelist) > 0:
        return pd.concat(granulelist)


def get_all_bathy_from_granule_parallel(filename):
    # find which beams are available in the netcdf file\
    beamlist = atl03_utils.get_beams(filename)
    granulelist = []
    with Pool(8) as pool:
        pool.map(lambda x: _apply_kde(filename, x), beamlist)
    # print(granulelist)
    if len(granulelist) > 0:
        return pd.concat(granulelist)


def bathy_from_all_tracks(path):
    dflist = []
    for filename in tqdm(iglob(path + "/ATL03/*.nc")):
        dflist.append(get_all_bathy_from_granule(filename))
    return pd.concat(dflist)


def bathy_from_all_tracks_parallel(path):
    filenamelist = list(iglob(path + "/ATL03/*.nc"))
    with Pool() as pool:
        result = pool.map(get_all_bathy_from_granule, filenamelist)

    if len(result) > 1:
        return pd.concat(result)
    elif len(result) == 1:
        return result


def run_multiple():
    paths = [
        "../data/test_sites/florida_keys",
        "../data/test_sites/PR",
        "../data/test_sites/North_aus",
        "../data/test_sites/PR_SE_corner",
    ]
    for path in paths:
        print("starting folder", path)
        combined_result = bathy_from_all_tracks_parallel(path)
        combined_result.to_file(path + "/all_bathy_pts.gpkg")

# %%
if __name__ == "__main__":
    bathy_from_all_tracks_parallel("../data/test_sites/PR_SE_corner").to_file(
        "../data/test_sites/PR_SE_corner"
    )
