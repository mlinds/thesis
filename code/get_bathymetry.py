# %%
import atl03_utils
from kde_peaks_method import get_elev_at_max_density
import pandas as pd
from glob import iglob
from tqdm import tqdm
from multiprocessing import Pool


def _filter_apply_kde(filename, beam):

    print(f"reading {beam} from {filename}")
    beamdata = atl03_utils.load_beam_array_ncds(filename, beam)

    point_dataframe = atl03_utils.add_track_dist_meters(beamdata,geodataframe=True)
    #  Filter any points over 5m above the geoid.
    point_dataframe = point_dataframe.bathy.filter_high_returns()

    point_dataframe = point_dataframe.bathy.filter_TEP()

    point_dataframe = point_dataframe.bathy.add_sea_level()

    point_dataframe = point_dataframe.bathy.filter_low_points()

    point_dataframe = point_dataframe.bathy.remove_surface_points(n=3)

    point_dataframe = point_dataframe.bathy.add_gebco()
    # filter points based on gebco
    point_dataframe = point_dataframe[point_dataframe.gebco_elev > -50]
    point_dataframe = point_dataframe[point_dataframe.gebco_elev < 6]

    # Recalculate the horizontal distance
    point_dataframe["dist_or"] = point_dataframe.dist_or - point_dataframe.dist_or.min()

    kde_elev = point_dataframe.Z_g.rolling(window=300, center=True).apply(
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
        bathy_pts = _filter_apply_kde(filename, beam)
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
        pool.map(lambda x:_filter_apply_kde(filename, x),beamlist)
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
    with Pool(8) as pool:
        result = pool.map(get_all_bathy_from_granule, filenamelist)
    return pd.concat(result)

def run_multiple():
    paths = ["../data/test_sites/florida_keys","../data/test_sites/PR","../data/test_sites/NE_aus","../data/test_sites/PR_SE"]
    for path in paths:
        combined_result = bathy_from_all_tracks_parallel(path)
        combined_result.to_file(path+'/all_bathy_pts.gpkg')

if __name__ == "__main__":
    run_multiple()
# %%
