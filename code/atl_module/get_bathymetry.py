# %%
from kde_peaks_method import get_elev_at_max_density
import pandas as pd
from glob import iglob
from tqdm import tqdm
from multiprocessing import Pool
import numpy as np
import point_dataframe_filters as dfilt
import geospatial_functions as geofn
from load_netcdf import get_beams
from load_netcdf import load_beam_array_ncds

def _filter_points(beamdata: np.ndarray) -> pd.DataFrame:
    """Remove points outside of the gebco nearshore zone, points that are invalied, or to high

    Args:
        beamdata (np.ndarray): structed ndarray recieved from the beam parsing function

    Returns:
        pd.DataFrame: pandas dataframe including the along-track distance
    """

    raw_photon_df = pd.DataFrame(beamdata)
    filtered_photon_df = raw_photon_df.pipe(geofn.add_track_dist_meters
                                    ).pipe(dfilt.add_sea_surface_level
                                    ).pipe(dfilt.remove_surface_points
                                    ).pipe(dfilt.filter_gebco,low_limit=-50,high_limit=5
                                    ).pipe(dfilt.filter_high_returns
                                    ).pipe(dfilt.filter_TEP)
    # reset 
    filtered_photon_df["dist_or"] = filtered_photon_df.dist_or - filtered_photon_df.dist_or.min()

    return filtered_photon_df


def get_kde_bathymetry(df):
    if df is None:
        return None

    kde_elev = df.Z_g.rolling(window=200, center=True).apply(
        get_elev_at_max_density, raw=True, kwargs={"threshold": 0.07}
    )

    df = df.assign(kde_seafloor=kde_elev)
    points_with_bathy = df[df.kde_seafloor.notna()]

    return points_with_bathy


def get_all_bathy_from_granule(filename):
    # find which beams are available in the netcdf file\
    beamlist = get_beams(filename)
    granulelist = []
    for beam in beamlist:
        print("analyzing beam", beam, "from file ", filename)
        beamarray = load_beam_array_ncds(filename=filename, beam=beam)
        bathy_pts = get_kde_bathymetry(_filter_points(beamarray))
        print(len(bathy_pts))
        if len(bathy_pts) > 0:
            granulelist.append(bathy_pts)
    # print(granulelist)
    print(len(granulelist), " granuales found with points in ", filename)
    if len(granulelist) > 0:
        return pd.concat(granulelist)
    else:
        return "no points in granule"


def bathy_from_all_tracks(path):
    dflist = []
    for filename in tqdm(iglob(path + "/ATL03/*.nc")):
        dflist.append(get_all_bathy_from_granule(filename))
    return pd.concat(dflist)


def bathy_from_all_tracks_parallel(folderpath):
    filenamelist = list(iglob(folderpath + "/ATL03/*.nc"))
    with Pool() as pool:
        result = pool.map(get_all_bathy_from_granule, filenamelist)
    print(result)
    result.remove("no points in granule")
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
    bathy_from_all_tracks_parallel("../data/test_sites/florida_keys")
