# %%
import xarray as xr
import geopandas as gpd

# %%
jarkus_path = "/home/mlinds/wsl_data/transect.nc"
ds = xr.open_dataset(jarkus_path)
# get a dataframe of the 2021 data
recent = ds.sel(time="2021-07-01T00:00:00.000000000").to_dataframe().dropna()

# %%
subset = ds.where(
    ds.areaname
    == b"Zeeuws-Vlaanderen                                                                                   ",
    drop=True,
)
subset_array = (
    subset.altitude.to_dataframe()
    .dropna()
    .reset_index()
    .rename(columns={"lat": "Y", "lon": "X", "altitude": "Z"})
    .drop(columns=["alongshore", "cross_shore"])
    .to_records(index=False)
)

# %%
ds.altitude.to_netcdf("/home/mlinds/wsl_data/transect_ncdf4.nc")

# %%
gdf = gpd.GeoDataFrame(
    recent,
    geometry=gpd.points_from_xy(recent.lon, recent.lat, recent.altitude, crs="EPSG:4326"),
)
# normalize the name strings and overwrite the dataframe
gdf = gdf.assign(
    areaname=[
        st.decode("ascii").strip().replace("/", "").replace(" ", "")
        for st in recent.areaname.tolist()
    ]
)
# get a list of unique names in the dataframe
namelist = gdf.areaname.unique().tolist()

# %%
# loop over the list of names, and save each area as a separate dataframe
for name in namelist:
    gdf.loc[gdf.areaname == name, ["altitude", "time_bathy", "geometry"]].to_file(
        f"../data/jarkus/jarkus-2021_{name}.gpkg"
    )

# %%
recent.reset_index().loc[:, ["altitude", "time_bathy", "geometry"]]
