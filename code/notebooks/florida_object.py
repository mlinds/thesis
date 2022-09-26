# %%
from atl_module import GebcoUpscaler

# %%


# %%
site = GebcoUpscaler("florida_keys", "../data/test_sites/florida_keys/in-situ-DEM/truth.vrt")

# %%
# site.download_ATL03()

# %%
# site.recalc_tracklines_gdf()

# %%
# from itertools import product
# # setup result dictionary
# result = {}
# # make an empty list for each result
# result['window']=[]
# result['perc_hconf']=[]
# result['min_kde']=[]
# result['rmse']=[]
# result['MAE']=[]

# # loop over the inner product of the
# for window,perc_h,kde_min in product([100,150,200],[20,40,60],[0.0,0.1,0.2]):
#     result['window'].append(window)
#     result['perc_hconf'].append(perc_h)
#     result['min_kde'].append(kde_min)
#     site.find_bathy_from_icesat(
#     window=window,
#     threshold_val=0.0,
#     req_perc_hconf=perc_h,
#     window_meters=None,
#     min_photons=None,
#     min_kde=kde_min,
#     save_result=False
#     )
#     site.lidar_rmse()
#     result['rmse'].append(site.rmse_icesat)
#     result['MAE'].append(site.mae_icesat)
#     print(result)

# pd.DataFrame(result).to_csv(f'../data/test_sites/{site.site}/error_stats.csv')

# %%
# site.find_bathy_from_icesat(
#     window=200,
#     threshold_val=0.0,
#     req_perc_hconf=40,
#     window_meters=None,
#     min_photons=None,
#     min_kde=0.1
# )
# site.lidar_error()
site.subset_gebco(hres=50)

# %%
# site.bathy_pts_gdf = site.bathy_pts_gdf.assign(z_kde = site.bathy_pts_gdf.z_kde - site.bathy_pts_gdf.dac_corr  + site.bathy_pts_gdf.tide_ocean_corr)

# %%
# %%time
site.kriging(
    npts=3000,
    kr_model="ok",
    samplemethod="dart",
    # variogram_parameters={'range':33000,'nugget':0.7,'sill':23},
)

# %%
site.kalman_update(1.5)
print(site.raster_rmse())
