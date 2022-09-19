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
parser.add_argument("-lrmse", "--lidar-rmse", action="store_true", default=False)
parser.add_argument(
    "-t",
    "--table-error-metrics",
    action="store_true",
    default=False,
    help="Write the final error statistics to a latex-formatted table in the tables folder",
)

parser.add_argument(
    "-geofig",
    "--generate-maps",
    action="store_true",
    default=False,
    help="Generate the geographic summary maps for the site for the results section",
)

args = parser.parse_args()

if args.verbose:
    logzero.loglevel(DEBUG)


site = GebcoUpscaler(
    f"../data/test_sites/{args.sitename}",
    args.sitename,
    f"../data/test_sites/{args.sitename}/in-situ-DEM/truth.vrt",
)
if args.download_atl03:
    site.download_ATL03()

if args.trackline_calc:
    # site.recalc_tracklines_gdf()
    site.calc_zsdpoints_by_tracks()
    # site.plot_tracklines()

if args.bathymetry_points:
    site.find_bathy_from_icesat(
        window=100,
        threshold_val=0.0,
        req_perc_hconf=0,
        window_meters=None,
        min_photons=None,
        min_kde=0.10,
        low_limit=-50,
        high_limit=1,
        rolling_window=200,
        max_sea_surf_elev=2,
        filter_below_z=-40,
        filter_below_depth=-40,
        min_ph_count=0,
        n=2.5,
        max_geoid_high_z=5,
    )

if args.lidar_rmse:
    # add the new data if its not already there
    site.add_truth_data()
    # find the error stats and plot them
    site.lidar_error()
    site.plot_lidar_error()
    site.write_lidar_error_tables()

if args.subset_gebco:
    requested_hres = args.subset_gebco[0]
    site.subset_gebco(hres=requested_hres)

if args.kriging:
    # run the kriging algorithm if requested from the command line
    site.kriging(
        npts=2000,
        samplemethod="random",
        kr_model="uk",
        variogram_parameters={"range": 10000, "nugget": 0.7, "sill": 23},
    )

if args.kalman_update:
    # get the assumed gebco uncertainty
    gebco_uncertainty = args.kalman_update[0]
    site.kalman_update(gebco_uncertainty)

if args.raster_rmse:
    print(site.raster_rmse(error_out=True, check_kriged=True))
    site.write_raster_error_tables()

if args.generate_maps:
    # redo the summary maps for the results/maybe an appendix
    site.plot_icesat_points()

if args.table_error_metrics:
    # rewrite the error tables
    site.write_error_tables()

# site.run_summary()
