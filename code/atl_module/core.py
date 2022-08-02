# going to keep the namespace as clean as possible
import os
from atl_module.bathymetry_extraction import icesat_bathymetry
from atl_module.geospatial_utils import raster_interaction
from atl_module.io.download import request_full_data_shapefile
from atl_module.ocean_color import add_secchi_depth_to_tracklines
from atl_module.plotting import error_lidar_pt_vs_truth_pt

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

# TODO could move this into the object __init__ method so that the log file is always in path when the obejct is created
run_logger = setup_logger(name="mainrunlogger", logfile="./run_log.log")


class GebcoUpscaler:
    """Object that contains a test site, and optionally a truth raster for comparison"""

    def __init__(self, site, truebathy=None):
        # rmse_naive is the RMSE error between the bilinear interpolation and the truth. when the object is created, it is set to none
        self.rmse_naive = None
        # set up the site name
        self.site_name = site.capitalize()
        # base folderpath to join with others
        self.folderpath = f"../data/test_sites/{site}"
        self.gebco_full_path = "/mnt/c/Users/maxli/OneDrive - Van Oord/Documents/thesis/data/GEBCO/GEBCO_2021_sub_ice_topo.nc"
        self.truebathy_path = truebathy
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
        """Request a data download with the extent determined by the AOI.gpkg in the folder"""
        request_full_data_shapefile(
            folderpath=self.folderpath, shapefile_filepath=self.AOI_path
        )

    def recalc_tracklines_gdf(self):
        """Recalculate the tracklines from the raw netcdf files in the ATLO3/ folder"""
        self.tracklines = make_gdf_from_ncdf_files(self.folderpath + "/ATL03/*.nc")
        try:
            self.tracklines = add_secchi_depth_to_tracklines(self.tracklines)
        except ValueError:
            print("Unable to get Secchi depth info")
        finally:
            self.tracklines.to_file(self.trackline_path, overwrite=True)

    def subset_gebco(self, hres: int):
        """Take a subset of GEBCO with the area determined by the extent of the tracklines.gpkg file in the main folder, resampled bilinearly to the requested resolution

        Args:
            hres (int): the horizontal (x and y) resolution of the subset
        """
        if self.bathy_pts_gdf is None:
            raise FileExistsError('Calculate bathymetry first')
        # cut out a section of GEBCO, reproject and resample
        raster_interaction.subset_gebco(
            folderpath=self.folderpath,
            bathy_pts=self.bathy_pts_gdf,
            epsg_no=self.epsg,
            hres=hres,
        )

    def find_bathy_from_icesat(
        self,
        window,
        threshold_val,
        req_perc_hconf,
        min_photons,
        window_meters,
        min_kde,
        save_result=True,
    ):
        run_params = {
            "window_size_photons": window,
            "threshhold value": threshold_val,
            "Required percentage high confidence ocean photons": req_perc_hconf,
            "minimum photons in distance window": min_photons,
            "window_horizontal": window_meters,
            "Minimum KDE to be considered": min_kde,
        }
        run_logger.info(
            f"site: {self.site_name} - Starting bathymetry signal finding with parameters: {run_params}"
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
                f"The bathymetry for {self.site_name} was sucessfully calculated with {run_params} and saved to {self.bathymetric_point_path}"
            )

    def kriging(self, npts,kr_model, **kwargs):
        """Subset the points using poisson disk sampling then run the kriging process and save the resulting depth and uncertainty raster to the folder of the site
            Additional kwargs are passed into the kriging function, so parameters can be supplied to that function
        Args:
            npts (int): The number of points to subset
        """
        run_logger.info(
            f"Kriging {self.site_name} site using {npts} points with crs {self.crs} with options {kwargs}"
        )
        kriging.krige_bathy(
            kr_model=kr_model,
            folderpath=self.folderpath,
            npts=npts,
            variogram_model="spherical",
            crs=self.crs,
            **kwargs,
        )

    def kalman_update(self, gebco_std: float) -> None:
        """Performed a kalman update assuming a certain constant value for the standard deviation of GEBCO

        Args:
            gebco_std (float): The assumed measurement error (standard deviation in meters) of GEBCO data
        """
        kalman.gridded_kalman_update(
            self.kalman_update_raster_path,
            self.bilinear_gebco_raster_path,
            self.kriged_raster_path,
            gebco_std,
        )
        run_logger.info(
            f"Sucessful Kalman update of GEBCO bathymetry for {self.site_name} using a gebco standard deviation of {gebco_std} saved to {self.kalman_update_raster_path}"
        )

    def lidar_error(self) -> dict:
        """Print the error between the LIDAR data and the truth data, and save the error metrics to the object calling it"""
        lidar_err_dict = error_calc.icesat_error_rms_mae(beam_df=self.bathy_pts_gdf)
        self.rmse_icesat = lidar_err_dict.get("RMSE")
        self.mae_icesat = lidar_err_dict.get("MAE")
        run_logger.info(
            f"{self.site_name}: RMSE between icesat and truth {self.rmse_icesat}, MAE: {self.mae_icesat}"
        )
        return pd.DataFrame(lidar_err_dict,index=[self.site_name])

    def add_truth_data(self):

        if self.truebathy_path is None:
            run_logger.info(
                "No truth data is available, so none was added to the bathymetry dataframe"
            )
        else:
            self.bathy_pts_gdf = error_calc.add_true_elevation(
                self.bathy_pts_gdf, self.truebathy_path, self.crs
            )
            run_logger.info(
                f"Truth data added to Bathymetric Points dataframe for site: {self.site_name}"
            )

    def raster_rmse(self, check_kriged=False,error_out=False):
        """Calculate the raster error metrics for the various rasters (the naive bilinear raster, then kalman updated raster, and the post-kriging raster)

        Because each operation is very expensive, they are only run when required/requested.

        Args:
            check_kriged (bool, optional): Calculate the RMSE and MAE error between the kriged raster and the truth raster. This is. Defaults to False.
        """

        self.rmse_kalman = error_calc.raster_RMSE_blocked(
            self.truebathy_path, self.kalman_update_raster_path, error_out=error_out
        )
        # this only needs to be calculated once, so only do it if this is the first time this object has been created
        if self.rmse_naive is None:
            self.rmse_naive = error_calc.raster_RMSE_blocked(
                self.truebathy_path, self.bilinear_gebco_raster_path,
            )
        else:
            print('GEBCO vs Truth RMSE already calculated, skipping')
        # only check this RMSE if required
        if check_kriged:
            self.rmse_kriged = error_calc.raster_RMSE_blocked(
                self.truebathy_path, self.kriged_raster_path
            )
        # if this is not requested, set a dicionary saying that
        else:
            self.rmse_kriged = {"RMSE": "Not Calculated", "MAE": "Not Calculated"}

        self.raster_error_summary = pd.DataFrame.from_dict(
            {
                "Naive Bilinear Interpolation": self.rmse_naive,
                "Kalman Updated Raster": self.rmse_kalman,
                "Kriged Raster": self.rmse_kriged,
            },
            orient="index",
        )
        run_logger.info(self.raster_error_summary.to_json())
        return self.raster_error_summary

    def plot_lidar_error(self):
        # the below can be moved to the object
        outpath = f"../document/figures/{self.site_name}_lidar_estimated_vs_truth.jpg"
        error_lidar_pt_vs_truth_pt(self.bathy_pts_gdf,self.site_name).get_figure().savefig(
            outpath,
            facecolor="white",
            bbox_inches="tight",
            dpi=800,
        )
        run_logger.info(f'{self.site_name}: Saved lidar error plot to {outpath}')

