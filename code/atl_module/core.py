# going to keep the namespace as clean as possible
import os

import geopandas as gpd
from fiona.errors import DriverError

from atl_module import (
    error_calc,
    icesat_bathymetry,
    kalman,
    kriging,
    ocean_color,
    raster_interaction,
)
from atl_module.geospatial_functions import (
    make_gdf_from_ncdf_files,
    to_refr_corrected_gdf,
)

# TODO add a RMS error between the points and truth data
# TODO add a function to automatically append the site error data to a table
class GebcoUpscaler:
    """Object that contains a test site, and optionally a truth raster for comparison"""

    def __init__(self, folderpath, truebathy=None):
        self.folderpath = folderpath
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
        # setup the files needed
        # try to add the tracklines, recalculate them if they're not present
        try:
            self.tracklines = gpd.read_file(self.trackline_path)
            self.crs = self.tracklines.estimate_utm_crs()
            self.epsg = self.crs.to_epsg()
        except DriverError:
            print("Trackline geodata not found - recalculating from netcdf files")
            self.get_tracklines_geom()
        #  try to add bathymetry points, print a message if they're not found
        try:
            self.bathy_pts_gdf = gpd.read_file(self.bathymetric_point_path)
        except:
            print("Bathy Points geodata not found: run `find_bathy_from_icesat()`")
            # self.find_bathy_from_icesat()

    def get_tracklines_geom(self):
        self.tracklines = make_gdf_from_ncdf_files(self.folderpath + "/ATL03/*.nc")
        self.crs = self.tracklines.estimate_utm_crs()
        # self.tracklines = ocean_color.add_secchi_depth_to_tracklines(self.tracklines)
        self.tracklines.to_file(self.trackline_path, overwrite=True)

    def subset_gebco(self):
        # cut out a section of GEBCO, reproject and resample
        raster_interaction.subset_gebco(
            folderpath=self.folderpath, tracklines=self.tracklines, epsg_no=self.epsg
        )

    def find_bathy_from_icesat(
        self, window, threshold_val, req_perc_hconf, min_photons, window_meters
    ):
        bathy_pts = icesat_bathymetry.bathy_from_all_tracks_parallel(
            self.folderpath,
            window=window,
            threshold_val=threshold_val,
            req_perc_hconf=req_perc_hconf,
            min_photons=min_photons,
            window_meters=window_meters,
        )
        bathy_gdf = to_refr_corrected_gdf(bathy_pts, crs=self.crs)
        # if there is no truth data, just assign, otherwise add the true elevation then add it
        if self.truebathy is None:
            self.bathy_pts_gdf = bathy_gdf
        else:
            self.bathy_pts_gdf = error_calc.add_true_elevation(
                bathy_gdf, self.truebathy
            )

        self.bathy_pts_gdf.to_file(self.bathymetric_point_path, overwrite=True)

    def kriging(self, npts):
        kriging.krige_bathy(
            krmodel=kriging.UniversalKriging,
            folderpath=self.folderpath,
            npts=npts,
            variogram_model="spherical",
            crs=self.crs,
        )

    def kalman(self, gebco_st):
        kalman.gridded_kalman_update(
            self.kalman_update_raster_path,
            self.bilinear_gebco_raster_path,
            self.kriged_raster_path,
            gebco_st,
        )

    def rmse_error(self):
        if self.truebathy is None:
            raise ValueError(
                "You need to provide a ground truth raster calculate the RMS error"
            )
        self.rmse_kalman = error_calc.raster_RMSE(
            self.truebathy, self.kalman_update_raster_path
        )
        self.rmse_naive = error_calc.raster_RMSE(
            self.truebathy, self.bilinear_gebco_raster_path
        )
        raster_summary = pd.DataFrame.from_dict(
            {
                "Naive Bilinear Interpolation": self.rmse_naive,
                "Kalman Updated Raster": self.rmse_kalman,
            },
            orient="index",
        )
        print(raster_summary)

    # def
