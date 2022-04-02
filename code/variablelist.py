#%%
beamlist = ["/gt1l", "/gt1r", "/gt2l", "/gt2r", "/gt3l", "/gt3r"]

varpaths = [
    'geolocation/segment_dist_x',
    'geolocation/segment_id',
    'geolocation/sigma_h',
    'heights/h_ph',
    'heights/lat_ph',
    'heights/lon_ph',
    'heights/dist_ph_along',
    'heights/delta_time',
    'geophys_corr/dem_h',
    'geophys_corr/tide_ocean',
]

coverage_requested = ''
for beam in beamlist:
    for path in varpaths:
        coverage_requested = coverage_requested + beam + '/' + path + ','

# %%
