import argparse

import logzero
from atl_module.core import GebcoUpscaler
from logzero import DEBUG

# runlogger = setup_logger(name="mainrunlogger", logfile="./run_log.log")
parser = argparse.ArgumentParser()
parser.add_argument("sitename", help="name of test site")
parser.add_argument(
    "-d",
    "--download_atl03",
    action="store_true",
    default=False,
    help="(Re)download the ATL03 data",
)
parser.add_argument("-v", "--verbose", action="store_true", default=False)

parser.add_argument("-tr", "--trackline-calc", action="store_true", default=False)

parser.add_argument("-b", "--bathymetry-points", action="store_true", default=False)

parser.add_argument(
    "-ka",
    "--kalman-update",
    type=float,
    nargs=1,
    default=False,
    help="Perform the Kalman updating with the specified standard deviation of GEBCO",
)

parser.add_argument(
    "-g",
    "--subset-gebco",
    nargs=1,
    type=int,
    default=False,
    help="Get the GEBCO grid over the area and resample bilinearly to the requested resolution",
)

parser.add_argument("-kr", "--kriging", action="store_true", default=False)

parser.add_argument("-rmse", "--raster-rmse", action="store_true", default=False)

args = parser.parse_args()

if args.verbose:
    logzero.loglevel(DEBUG)


site = GebcoUpscaler(
    f"{args.sitename}",
    f"../data/test_sites/{args.sitename}/in-situ-DEM/truth.vrt",
)
if args.download_atl03:
    site.download_ATL03()

if args.trackline_calc:
    site.recalc_tracklines_gdf()

if args.bathymetry_points:
    site.find_bathy_from_icesat(
        window=150,
        threshold_val=0.0,
        req_perc_hconf=0,
        window_meters=None,
        min_photons=None,
        min_kde=0.1,
        low_limit=-40,
        high_limit=2,
        rolling_window=200,
        max_sea_surf_elev=2,
        filter_below_z=-60,
        filter_below_depth=-60,
        min_ph_count=35,
        n=1,
        max_geoid_high_z=5,
    )

    print(site.lidar_error())

if args.subset_gebco:
    requested_hres = args.subset_gebco[0]
    site.subset_gebco(hres=requested_hres)

if args.kriging:
    site.kriging(
        npts=1800,
        samplemethod="dart",
        kr_model="uk",
        variogram_parameters={"range": 10000, "nugget": 0.7, "sill": 23},
    )

if args.kalman_update:
    gebco_uncertainty = args.kalman_update[0]
    site.kalman_update(gebco_uncertainty)

if args.raster_rmse:

    print(site.raster_rmse())

# site.run_summary()
