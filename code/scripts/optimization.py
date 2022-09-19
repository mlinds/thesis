from itertools import product

import pandas as pd
from atl_module import GebcoUpscaler


def optimize_params(site_name):
    resultlist = []
    site = GebcoUpscaler(site_name, f"../data/test_sites/{site_name}/in-situ-DEM/truth.vrt")

    windows = [100, 150, 200]
    min_kdes = [0.1, 0.15]
    n_vals = [1.5, 2]
    # lowlimits = [-40, -50]
    for win, minkde, n in product(windows, min_kdes, n_vals):

        site.find_bathy_from_icesat(
            window=win,
            threshold_val=0.0,
            req_perc_hconf=0,
            window_meters=None,
            min_photons=None,
            min_kde=minkde,
            low_limit=-50,
            high_limit=3,
            rolling_window=200,
            max_sea_surf_elev=2,
            filter_below_z=-40,
            filter_below_depth=-40,
            min_ph_count=0,
            n=n,
            max_geoid_high_z=5,
            save_result=False,
        )
        site.lidar_error()
        nphotons = len(site.bathy_pts_gdf)
        site.run_params["n_bathypts"] = nphotons
        site.run_params["sitename"] = site_name
        # print(site.lidar_err_dict,site.run_params)
        resultlist.append(site.lidar_err_dict | site.run_params)

    pd.DataFrame(resultlist).to_csv(f"{site_name}_optimization.csv")


if __name__ == "__main__":
    sites = ["florida_keys", "stcroix", "charlotteamalie"]
    # sites = ['oahu1','oahu2','oahu3','oahu4']
    # sites = ['oahu5','oahu6','oahu7','oahu8']
    for sitename in sites:
        optimize_params(sitename)
