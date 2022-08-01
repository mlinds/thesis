# %%
import xarray as xr
import geopandas as gpd
import pdal 
# %%
jarkus_path = "/home/mlinds/wsl_data/transect.nc"
ds = xr.open_dataset(jarkus_path)
# get a dataframe of the 2021 data
recent = ds.sel(time="2021-07-01T00:00:00.000000000").to_dataframe().dropna().rename(columns={"lat": "Y", "lon": "X", "altitude": "Z"})

# %%
gdf = gpd.GeoDataFrame(
    recent,
    geometry=gpd.points_from_xy(
        recent.X, recent.Y, recent.Z, crs="EPSG:4326"
    ),
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
