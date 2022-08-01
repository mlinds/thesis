# going to keep the namespace as clean as possible
import os
from atl_module.bathymetry_extraction import icesat_bathymetry
from atl_module.geospatial_utils import raster_interaction
from atl_module.io.download import request_full_data_shapefile
from atl_module.ocean_color import add_secchi_depth_to_tracklines

import geopandas as gpd
import pandas as pd
from fiona.errors import DriverError
from logzero import setup_logger, logger

from os.path import exists as file_exists

from atl_module import (
    error_calc,
    kalman,
    kriging,
)
from atl_module.geospatial_utils.geospatial_functions import (
    make_gdf_from_ncdf_files,
    to_refr_corrected_gdf,
)

run_logger = setup_logger(name="mainrunlogger", logfile="./run_log.log")

# TODO add a function to automatically append the site error data to a table
class GebcoUpscaler:
    """Object that contains a test site, and optionally a truth raster for comparison"""

    def __init__(self, site, truebathy=None):
        self.site = site
        self.folderpath = f'../data/test_sites/{site}'
        self.gebco_full_path = "/mnt/c/Users/maxli/OneDrive - Van Oord/Documents/thesis/data/GEBCO/GEBCO_2021_sub_ice_topo.nc"
        self.truebathy = truebathy
        # set up the paths of the relevant vector files:
        self.trackline_path = os.path.join(self.folderpath, "tracklines.gpkg")
        self.bathymetric_point_path = os.path.join(
            self.folderpath, "all_bathy_pts.gpkg"
        )
        # raster paths
        self.kalman_update_raster_path = os.path.join(
            self.folderpath, "kalman_updated.tif"
        )
        self.bilinear_gebco_raster_path = os.path.join(self.folderpath, "bilinear.tif")
        self.kriged_raster_path = os.path.join(self.folderpath, "kriging_output.tif")
        self.AOI_path = os.path.join(self.folderpath, "AOI.gpkg")
        # setup the files needed
        # try to add the tracklines
        if file_exists(self.trackline_path):
            self.tracklines = gpd.read_file(self.trackline_path)
            self.crs = self.tracklines.estimate_utm_crs()
            self.epsg = self.crs.to_epsg()
        else:
            run_logger.info(
                "Trackline geodata not found - recalculate from netcdf files"
            )

        #  try to add bathymetry points, print a message if they're not found
        if file_exists(self.bathymetric_point_path):
            self.bathy_pts_gdf = gpd.read_file(self.bathymetric_point_path)
        else:
            print("Bathy Points geodata not found: run `find_bathy_from_icesat()`")
            # self.find_bathy_from_icesat()
        # check if the interpolated gebco exists
        if not file_exists(self.bilinear_gebco_raster_path):
            print("should subset gebco")
            # self.subset_gebco()

    def download_ATL03(self):
        request_full_data_shapefile(
            folderpath=self.folderpath, shapefile_filepath=self.AOI_path
        )

    def recalc_tracklines_gdf(self):
        self.tracklines = make_gdf_from_ncdf_files(self.folderpath + "/ATL03/*.nc")
        try:
            self.tracklines = add_secchi_depth_to_tracklines(self.tracklines)
        except ValueError:
            print("Unable to get Secchi depth info")
        finally:
            self.tracklines.to_file(self.trackline_path, overwrite=True)

    def subset_gebco(self, hres):
        # cut out a section of GEBCO, reproject and resample
        raster_interaction.subset_gebco(
            folderpath=self.folderpath,
            tracklines=self.tracklines,
            epsg_no=self.epsg,
            hres=hres,
        )

    def find_bathy_from_icesat(
        self, window, threshold_val, req_perc_hconf, min_photons, window_meters, min_kde,save_result=True
    ):
        run_logger.info(f"site: {self.site} - Starting bathymetry signal finding with parameters:")
        run_logger.info(
            {
                "Site Name":self.site,
                "window_size_photons": window,
                "threshhold value": threshold_val,
                "Required percentage high confidence ocean photons": req_perc_hconf,
                "minimum photons in distance window": min_photons,
                "window_horizontal": window_meters,
                "Minimum KDE to be considered": min_kde,
            },
        )
        bathy_pts = icesat_bathymetry.bathy_from_all_tracks_parallel(
            self.folderpath,
            window=window,
            threshold_val=threshold_val,
            req_perc_hconf=req_perc_hconf,
            min_photons=min_photons,
            window_meters=window_meters,
            min_kde=min_kde,
        )
        bathy_gdf = to_refr_corrected_gdf(bathy_pts, crs=self.crs)
        # assign the resulting datframe to the object
        self.bathy_pts_gdf = bathy_gdf
        # try to add the elevation from the truth DEM
        self.add_truth_data()
        # write the bathymetric points to a file
        if save_result: 
            self.bathy_pts_gdf.to_file(self.bathymetric_point_path, overwrite=True)
            run_logger.info(
                f"The bathymetry for {self.site} was calculated and saved to {self.bathymetric_point_path}"
            )

    def kriging(self, npts, **kwargs):
        """Subset the points using poisson disk sampling then run the kriging process and save the resulting depth and uncertainty raster to the folder of the site
            Additional kwargs are passed into the kriging function, so parameters can be supplied to that function
        Args:
            npts (int): The number of points to subset
        """
        run_logger.info(
            f"Kriging {self.site} site using {npts} points with crs {self.crs} with options {kwargs}"
        )
        kriging.krige_bathy(
            krmodel=kriging.UniversalKriging,
            folderpath=self.folderpath,
            npts=npts,
            variogram_model="spherical",
            crs=self.crs,
            **kwargs,
        )

    def kalman_update(self, gebco_st):
        run_logger.info(
            f"Updating GEBCO bathymetry for {self.site} using a gebco standard deviation of {gebco_st}"
        )
        kalman.gridded_kalman_update(
            self.kalman_update_raster_path,
            self.bilinear_gebco_raster_path,
            self.kriged_raster_path,
            gebco_st,
        )

    def lidar_rmse(self):
        self.rmse_icesat = error_calc.icesat_rmse(
            bathy_points=self.bathy_pts_gdf,
        )
        self.mae_icesat = error_calc.icesat_mae(bathy_points=self.bathy_pts_gdf)
        run_logger.info(
            f"{self.site}: RMSE between icesat and truth {self.rmse_icesat}, MAE: {self.mae_icesat}"
        )

    def add_truth_data(self):

        if self.truebathy is None:
            run_logger.info(
                "No truth data is available, so none was added to the bathymetry dataframe"
            )
        else:
            self.bathy_pts_gdf = error_calc.add_true_elevation(
                self.bathy_pts_gdf, self.truebathy, self.crs
            )
            run_logger.info(f"Truth data added to Bathymetric Points dataframe for site: {self.site}")

    def raster_rmse(self):
        # run_logger.info("")

        self.rmse_kalman = error_calc.raster_RMSE_blocked(
            self.truebathy, self.kalman_update_raster_path
        )
        self.rmse_naive = error_calc.raster_RMSE_blocked(
            self.truebathy, self.bilinear_gebco_raster_path
        )
        self.rmse_kriged = error_calc.raster_RMSE_blocked(
            self.truebathy, self.kriged_raster_path
        )
        self.raster_error_summary = pd.DataFrame.from_dict(
            {
                "Naive Bilinear Interpolation": self.rmse_naive,
                "Kalman Updated Raster": self.rmse_kalman,
                "Kriged Raster": self.rmse_kriged   ,
            },
            orient="index",
        )
        run_logger.info(self.raster_error_summary.to_json())
