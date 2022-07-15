from atl_module.core import GebcoUpscaler
import argparse
import logzero
from logzero import setup_logger

runlogger = setup_logger(name="mainrunlogger", logfile="./run_log.log")
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
    logzero.loglevel()
runlogger.info(f"Starting run for test site {args.sitename}")
site = GebcoUpscaler(
    f"../data/test_sites/{args.sitename}/",
    f"../data/test_sites/{args.sitename}/in-situ-DEM/truth.vrt",
)

site.find_bathy_from_icesat(
    window=100,
    threshold_val=0.0,
    req_perc_hconf=70,
    window_meters=None,
    min_photons=None,
)
# site.subset_gebco()
# site.kriging(npts=300)
# site.kalman(1.5)
# site.rmse_error()
