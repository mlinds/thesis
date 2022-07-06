# going to keep the namespace as clean as possible
from atl_module import icesat_bathymetry
from atl_module import kriging
from atl_module import kalman
from atl_module.geospatial_functions import to_refr_corrected_gdf
from atl_module import error_calc


class GebcoUpscaler:
    # TODO add method to make a geodataframe of the tracks
    # TODO add method to get UTM from the track geodataframe
    # TODO method to subset GEBCO and reproject it to the needed UTM zone
    def __init__(self, folderpath, truebathy=None):
        self.folderpath = folderpath
        self.gebco_full_path = "/mnt/c/Users/maxli/OneDrive - Van Oord/Documents/thesis/data/GEBCO/GEBCO_2021_sub_ice_topo.nc"
        self.truebathy = truebathy

    # eventually change this to read from the saved file
    def find_bathy_from_icesat(self, window, threshold_val, req_perc_hconf):
        bathy_pts = icesat_bathymetry.bathy_from_all_tracks_parallel(
            self.folderpath,
            window=window,
            threshold_val=threshold_val,
            req_perc_hconf=req_perc_hconf,
        )
        bathy_gdf = to_refr_corrected_gdf(bathy_pts, crs="EPSG:32617")
        if self.truebathy is None:
            self.bathy_pts_gdf = bathy_gdf
        else:
            self.bathy_pts_gdf = error_calc.add_true_elevation(bathy_gdf, truebathy)

        self.bathy_pts_gdf.to_file(
            self.folderpath + "/all_bathy_pts.gpkg", overwrite=True
        )

    def kriging(self, npts):
        kriging.krige_bathy(
            krmodel=kriging.UniversalKriging,
            initial_raster_path=self.folderpath + "/bilinear.tif",
            folderpath=self.folderpath,
            npts=npts,
            variogram_model="linear",
            outraster_path=self.folderpath + "/kriged.tif",
        )

    def kalman(self, gebco_st):
        kalman.gridded_kalman_update(
            self.folderpath + "/kalman_updated.tif",
            self.folderpath + "/bilinear.tif",
            self.folderpath + "/interp_OK.tif",
            gebco_st,
        )

    def rmse_error(self):
        self.rmse_kalman = error_calc.raster_RMSE(
            self.truebathy, self.folderpath + "/kalman_updated.tif"
        )
        self.rmse_naive = error_calc.raster_RMSE(
            self.truebathy, self.folderpath + "/kalman_updated.tif"
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
