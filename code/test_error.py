# %%
from atl_module import icesat_bathymetry
from atl_module.raster_interaction import query_raster
from atl_module.geospatial_functions import (
    to_refr_corrected_gdf,
)
import pandas as pd
from atl_module.error_calc import calc_rms_error
from glob import iglob
from sklearn.metrics import mean_absolute_error

# %%
folderpath = "../data/test_sites/Martinique"
resultdict = {}

resultdict["Threshold value"] = []
resultdict["RMS Error"] = []
# resultdict['MAE Error'] = []

for windowval in [100, 200]:
    # get_bathymetry
    bathy_points = icesat_bathymetry.bathy_from_all_tracks_parallel(
        folderpath, window=windowval, threshold_val=0.0, req_perc_hconf=60
    )

    true_bathy = query_raster(
        bathy_points,
        src="../data/test_sites/Martinique/in-situ-dem/DONNEES/MNT_ANTS100m_HOMONIM_WGS84_PBMA_ZNEG.asc",
    )

    bathy_points = bathy_points.assign(fema_elev=true_bathy)
    bathy_points = bathy_points[bathy_points.fema_elev != -9999.0]

    bathy_points.eval("error = z_kde-fema_elev", inplace=True)
    rms = calc_rms_error(bathy_points, ["fema_elev"])
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
