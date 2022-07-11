# going to keep the namespace as clean as possible
from atl_module import icesat_bathymetry
from atl_module import kriging
from atl_module import kalman
from atl_module.geospatial_functions import to_refr_corrected_gdf,make_gdf_from_ncdf_files
from atl_module import error_calc
from atl_module import raster_interaction
import geopandas as gpd
from fiona.errors import DriverError


class GebcoUpscaler:
    # TODO add method to make a geodataframe of the tracks
    # TODO add method to get UTM from the track geodataframe
    # TODO method to subset GEBCO and reproject it to the needed UTM zone
    def __init__(self, folderpath, truebathy=None):
        self.folderpath = folderpath
        self.gebco_full_path = "/mnt/c/Users/maxli/OneDrive - Van Oord/Documents/thesis/data/GEBCO/GEBCO_2021_sub_ice_topo.nc"
        self.truebathy = truebathy
        # set up the paths of the relevant files:
        self.trackline_path = self.folderpath+'/tracklines.gpkg'
        self.bathymetric_point_path = self.folderpath + "/all_bathy_pts.gpkg"
        # raster paths
        self.kalman_update_raster_path = self.folderpath + "/kalman_updated.tif"
        self.bilinear_gebco_raster_path = self.folderpath + "/bilinear.tif"
        self.kriged_raster_path = self.folderpath + "/kriging_output.tif"
        # setup the files needed
        try:
            self.tracklines = gpd.read_file(self.trackline_path)
        except DriverError:
            print('Trackline geodata not found - recalculating from netcdf files')
            self.get_tracklines_geom()
        try:
            self.bathy_pts_gdf = gpd.read_file(self.bathymetric_point_path)
        except:
            print('Bathy Points geodata not found: run `find_bathy_from_icesat()`')
            # self.find_bathy_from_icesat()

    def get_tracklines_geom(self):
        self.tracklines = make_gdf_from_ncdf_files(self.folderpath+'/ATL03/*.nc')
        self.crs = self.tracklines.estimate_utm_crs()
        self.tracklines.to_file(self.trackline_path,overwrite=True)
    
    def subset_gebco(self):
        # cut out a section of GEBCO, reproject and resample
        raster_interaction.subset_gebco(self.folderpath,self.tracklines)

    def find_bathy_from_icesat(self, window, threshold_val, req_perc_hconf):
        bathy_pts = icesat_bathymetry.bathy_from_all_tracks_parallel(
            self.folderpath,
            window=window,
            threshold_val=threshold_val,
            req_perc_hconf=req_perc_hconf,
        )
        bathy_gdf = to_refr_corrected_gdf(bathy_pts, crs=self.crs)
        if self.truebathy is None:
            self.bathy_pts_gdf = bathy_gdf
        else:
            self.bathy_pts_gdf = error_calc.add_true_elevation(bathy_gdf, truebathy)

        self.bathy_pts_gdf.to_file(
            self.bathymetric_point_path, overwrite=True
        )

    def kriging(self, npts):
        kriging.krige_bathy(
            krmodel=kriging.UniversalKriging,
            folderpath=self.folderpath,
            npts=npts,
            variogram_model="spherical",
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
            raise ValueError('You need to provide a ground truth raster calculate the RMS error')
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
