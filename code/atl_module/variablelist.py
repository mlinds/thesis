#%%
beamlist = ["/gt1l", "/gt1r", "/gt2l", "/gt2r", "/gt3l", "/gt3r"]

varpaths = [
    "geolocation/segment_dist_x",
    "geolocation/segment_id",
    "geolocation/sigma_h",
    "geolocation/ref_azimuth",
    "geolocation/ref_elev",
    "geolocation/segment_ph_count",
    "heights/h_ph",
    "heights/lat_ph",
    "heights/lon_ph",
    "heights/dist_ph_along",
    "heights/delta_time",
    "heights/signal_conf_ph",
    # "heights/quality_ph",
    "geophys_corr/dem_h",
    "geophys_corr/tide_ocean",
    "geophys_corr/delta_time",
    "geophys_corr/geoid",
    "geophys_corr/geoid_free2mean",
]

coverage_requested = "/ancillary_data/start_rgt/,/ancillary_data/end_rgt/,/ancillary_data/data_start_utc/,/ancillary_data/data_end_utc/,/quality_assessment/qa_granule_pass_fail/,/quality_assessment/gt1l/,/quality_assessment/gt1r/,/quality_assessment/gt2l/,/quality_assessment/gt2r,/quality_assessment/gt3l/,/quality_assessment/gt3r,/orbit_info/"
for beam in beamlist:
    for path in varpaths:
        coverage_requested = coverage_requested + beam + "/" + path + ","

# %%
segment_vars = ""
for beam in beamlist:
    segment_vars = (
        segment_vars
        + f"/ancillary_data/data_start_utc/,{beam}/geolocation/reference_photon_lat/,{beam}/geolocation/reference_photon_lon/,{beam}/geolocation/delta_time/,{beam}/geolocation/segment_ph_cnt/,{beam}/geolocation/surf_type/,"
    )
