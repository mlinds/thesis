import icepyx as ipx


# gee_bbox = [[-79.329529, 22.178662],
#  [-78.725281, 22.178662],
#  [-78.725281, 22.432768],
#  [-79.329529, 22.432768],
#  [-79.329529, 22.178662]]


gee_bbox = [
    -78.40391706006527,
    21.886167056716133,
    -77.86778421403766,
    22.576108370765198,
]
product = "ATL03"
datapath = "./data/icepyxtest/"
pattern = (
    "processed_"
    + product
    + "_{datetime:%Y%m%d%H%M%S}_{rgt:4}{cycle:2}{orbitsegment:2}_{version:3}_{revision:2}.h5"
)

# including for completeness
region_a = ipx.Query(
    product,
    gee_bbox,
    ["2021-12-16", "2021-12-18"],
    start_time="00:00:00",
    end_time="23:59:59",
)
region_a.earthdata_login(uid="maelinds", email="max.lindsay95@gmail.com")
region_a.download_granules(path=datapath)
reader = ipx.Read(data_source=datapath, product=product, filename_pattern=pattern)
reader.vars.append(beam_list=["gt1l", "gt3r"], var_list=["h_ph", "lat_ph", "lon_ph"])


out = reader.load()
