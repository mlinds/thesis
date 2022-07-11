# %%
from pykrige.ok import OrdinaryKriging
from pykrige.uk import UniversalKriging

# from pykrige.rk import RegressionKriging
import geopandas as gpd
import rasterio
import rioxarray
import pdal


def prepare_pt_subset_for_kriging(folderpath, npts):
    pts_gdf_all = gpd.read_file(f"{folderpath}/all_bathy_pts.gpkg")

    # create a numpy array that PDAL can read by subsetting the columns and renaming the northing, easting, etc columns to the LAS defaults (Z,Y,Z)
    pdal_array = (
        pts_gdf_all.loc[:, ["northing", "easting", "z_kde"]]
        .rename(columns={"northing": "Y", "easting": "X", "z_kde": "Z"})
        .to_records(index=False)
    )

    # 1st pdal pipeline culls the dataset to a fixed number of points
    pipeline = pdal.Filter.relaxationdartthrowing(count=npts).pipeline(pdal_array)

    print(pipeline.execute(), "points remaining after relaxation dart throwing culling")
    # get the thinned points from the output
    thinned_array = pipeline.arrays[0]
    #
    pts_gdf = gpd.GeoDataFrame(
        thinned_array,
        geometry=gpd.points_from_xy(
            thinned_array["X"], thinned_array["Y"], crs="EPSG:32617"
        ),
    )
<<<<<<< HEAD
    pts_gdf.to_file(folderpath + "/keys_testpts.gpkg")
    pipeline = pdal.Writer.las(filename=folderpath + "/filtered.laz").pipeline(
=======
    pts_gdf.to_file("../data/resample_test/keys_testpts.gpkg")
    pipeline = pdal.Writer.las(filename="../data/resample_test/filtered.laz").pipeline(
>>>>>>> d54fd8667c869c15d20e6279a500c90ed38c029e
        thinned_array
    )
    print(pipeline.execute(), "Points written to output LAZ and geopackage files")

    return pts_gdf


<<<<<<< HEAD
def krige_bathy(krmodel, folderpath, npts, variogram_model):
=======
def krige_bathy(krmodel, initial_raster_path, pointfolder_path, npts, variogram_model):
>>>>>>> d54fd8667c869c15d20e6279a500c90ed38c029e
    """Load the bathymetric points, select a subset of them via PDAL poisson dart-throwing, then krige using pykrige

    Args:
        krmodel (KrigingModel): A kriging model from pykrige
        initial_raster_path (str): path of the starting point raster
        pointfolder_path (_type_): path of the location of the bathymetric points
        npts (integer): number of points to subset from the bathymetric points
    """
    # TODO raise an error if CRSs don't match

    # load the points for kriging
<<<<<<< HEAD
    pts_gdf = prepare_pt_subset_for_kriging(folderpath, npts)

    # open the interpolated raster to get the coordinates
    with rasterio.open(folderpath + "/bilinear.tif") as ras:
=======
    pts_gdf = prepare_pt_subset_for_kriging(pointfolder_path, npts)

    # open the interpolated raster to get the coordinates
    with rasterio.open(initial_raster_path) as ras:
>>>>>>> d54fd8667c869c15d20e6279a500c90ed38c029e
        ar = rioxarray.open_rasterio(ras)
        gridx = ar.x.data
        gridy = ar.y.data
    # read the xyz locations of the points
    x_loc = pts_gdf.geometry.x.to_numpy()
    y_loc = pts_gdf.geometry.y.to_numpy()
    z_elev = pts_gdf.Z.to_numpy()
    # run whichever kriging model is chosen
    krigemodel = krmodel(
        x=x_loc,
        y=y_loc,
        z=z_elev,
        variogram_model=variogram_model,
        verbose=True,
        # coordinates_type="euclidean",
    )
    # get the output Zgrid and uncertainty
    z, ss = krigemodel.execute("grid", gridx, gridy)

    print("finished kriging, now saving the file")

    # save the results as a raster with band 1 and the Z value and band 2 as the uncertainty
    with rasterio.open(
<<<<<<< HEAD
        folderpath + "/kriging_output.tif",
=======
        "../data/resample_test/interp_OK.tif",
>>>>>>> d54fd8667c869c15d20e6279a500c90ed38c029e
        mode="w+",
        crs=ras.crs,
        width=ras.width,
        height=ras.height,
        count=2,
        dtype=ras.dtypes[0],
        transform=ras.transform,
    ) as rasout:
        rasout.write(z, 1)
        rasout.write(ss, 2)
    ras.close()
    print("Output raster of kriged Z values and uncertainty saved sucessfully")


if __name__ == "__main__":
    krige_bathy(
<<<<<<< HEAD
        krmodel=UniversalKriging,
        variogram_model="spherical",
        folderpath="../data/test_sites/florida_keys",
=======
        krmodel=OrdinaryKriging,
        variogram_model="linear",
        initial_raster_path="../data/resample_test/bilinear.tif",
        pointfolder_path="../data/test_sites/florida_keys",
>>>>>>> d54fd8667c869c15d20e6279a500c90ed38c029e
        npts=2000,
    )
