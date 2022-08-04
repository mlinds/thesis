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
    f"args.sitename",
    f"../data/test_sites/{args.sitename}/in-situ-DEM/truth.vrt",
)
# site.download_ATL03()
# site.recalc_tracklines_gdf()
# site.subset_gebco(hres=50)
site.find_bathy_from_icesat(
    window=100,
    threshold_val=0.0,
    req_perc_hconf=70,
    window_meters=None,
    min_photons=None,
)
print(site.lidar_error())
site.kriging(npts=1000, samplemethod="dart")
site.kalman_update(1.5)
print(site.raster_rmse())
