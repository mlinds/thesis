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

args = parser.parse_args()

if args.verbose:
    logzero.loglevel(DEBUG)


site = GebcoUpscaler(
    f"{args.sitename}",
    # f"../data/test_sites/oahu/in-situ-DEM/truth.vrt",
)
if args.download_atl03:
    site.download_ATL03()
site.recalc_tracklines_gdf()
# site.find_bathy_from_icesat(
#     window=200,
#     threshold_val=0.0,
#     req_perc_hconf=0,
#     window_meters=None,
#     min_photons=None,
#     min_kde=0.1,
#     low_limit=-40,
#     high_limit=2,
#     rolling_window=200,
#     max_sea_surf_elev=1,
#     filter_below_z=-40,
#     filter_below_depth=-40,
#     min_ph_count=35,
#     n=1,
#     max_geoid_high_z=5,
# )
# site.subset_gebco(hres=50)
# print(site.lidar_error())
# site.plot_lidar_error()
# site.kriging(npts=1800, samplemethod="dart", kr_model="uk")
# site.kalman_update(1)
# print(site.raster_rmse())
# site.run_summary()
