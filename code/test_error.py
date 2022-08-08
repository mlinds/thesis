# %%
import geopandas as gpd
import pandas as pd
from atl_module.bathymetry_extraction import icesat_bathymetry
from atl_module.error_calc import icesat_error_rms_mae
from atl_module.geospatial_utils.geospatial_functions import to_refr_corrected_gdf
from atl_module.geospatial_utils.raster_interaction import query_raster

# %%
folderpath = "../data/test_sites/florida_keys"
resultdict = {}

resultdict["Threshold value"] = []
resultdict["RMS Error"] = []
# resultdict['MAE Error'] = []

for windowval in [150]:
    # get_bathymetry
    bathy_points = icesat_bathymetry.bathy_from_all_tracks_parallel(
        folderpath,
        window=windowval,
        threshold_val=0.0,
        req_perc_hconf=40,
        window_meters=None,
        min_photons=None,
    )

    true_bathy = query_raster(
        bathy_points,
        src="../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt",
    )

    bathy_points = bathy_points.assign(fema_elev=true_bathy)
    bathy_points = bathy_points[bathy_points.fema_elev != -9999.0]

    bathy_points.eval("error = z_kde-fema_elev", inplace=True)
    rms = icesat_error_rms_mae(bathy_points, ["fema_elev"])
    # mae = mean_absolute_error(bathy_points.fema_elev,bathy_points.z_kde)

    resultdict["Threshold value"].append(windowval)
    resultdict["RMS Error"].append(rms)
    # resultdict['MAE Error'].append(mae)

df = pd.DataFrame(resultdict)
# %%
gdf = to_refr_corrected_gdf(bathy_points, crs="EPSG:32617")

gdf.to_file(folderpath + "/all_bathy_pts.gpkg", overwrite=True)

# %%
gdf.error.plot.hist(bins=50)

bathy_points.plot.scatter(
    y="z_kde", x="fema_elev", figsize=(20, 20), c="kde_val", cmap="viridis"
)
# %%
join1 = (
    bathy_points.assign(date=bathy_points.delta_time.dt.date)
    .astype({"date": "string"})
    .set_index(["date", "beam"])
)
join2 = (
    gpd.read_file("../data/global_analysis/color_points_mean.gpkg")
    .rename({"beamtype": "beam"}, axis=1)
    .set_index(["date", "beam"])
    .zsd
)
merged = pd.merge(join1, join2, right_index=True, left_index=True, how="left")

error_df = (
    merged.eval("error=error**2").groupby(["date", "beam"]).mean().eval("error=error**(0.5)")
)

error_df.plot.scatter(y="error", x="zsd")
error_df.plot.scatter(y="error", x="oc_hconf_perc")
error_df.plot.scatter(y="error", x="kde_val")
