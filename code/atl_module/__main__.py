from atl_module.core import GebcoUpscaler
import argparse
import logzero
from logzero import setup_logger, DEBUG

# runlogger = setup_logger(name="mainrunlogger", logfile="./run_log.log")
parser = argparse.ArgumentParser()
parser.add_argument("sitename", help="name of test site")
parser.add_argument(
    "-r",
    "--recalc",
    action="store_true",
    default=False,
    help="Force recalculation of all the intermediate steps",
)
parser.add_argument("-v", "--verbose", action="store_true", default=False)

args = parser.parse_args()

if args.verbose:
    logzero.loglevel(DEBUG)


site = GebcoUpscaler(
    f"{args.sitename}",
    f"../data/test_sites/oahu/in-situ-DEM/truth.vrt",
)
# site.download_ATL03()
# site.recalc_tracklines_gdf()
# site.subset_gebco(hres=50)
site.find_bathy_from_icesat(
    window=200,
    threshold_val=0.0,
    req_perc_hconf=60,
    window_meters=None,
    min_photons=None,
    min_kde=0.0,
    low_limit=-40,
    high_limit=2,
    rolling_window=200,
    max_sea_surf_elev=1,
    filter_below_z=-80,
    filter_below_depth=-80,
    n=1,
    max_geoid_high_z=5,
)
site.subset_gebco(hres=50)
print(site.lidar_error())
site.plot_lidar_error()
site.kriging(npts=1800, samplemethod="dart", kr_model="uk")
site.kalman_update(0.75)
print(site.raster_rmse(error_out=True))
