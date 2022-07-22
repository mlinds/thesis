# from pykrige.rk import RegressionKriging
import geopandas as gpd
import pdal
import rasterio
import rioxarray
from logzero import setup_logger
from pykrige.ok import OrdinaryKriging
from pykrige.uk import UniversalKriging

detail_logger = setup_logger(name="details")


def prepare_pt_subset_for_kriging(folderpath, npts, crs):
    pts_gdf_all = gpd.read_file(f"{folderpath}/all_bathy_pts.gpkg")

    # create a numpy array that PDAL can read by subsetting the columns and renaming the northing, easting, etc columns to the LAS defaults (Z,Y,Z)
    pdal_array = (
        pts_gdf_all.loc[:, ["northing", "easting", "z_kde"]]
        .rename(columns={"northing": "Y", "easting": "X", "z_kde": "Z"})
        .to_records(index=False)
    )

    # 1st pdal pipeline culls the dataset to a fixed number of points
    pipeline = pdal.Filter.relaxationdartthrowing(count=npts).pipeline(pdal_array)
    npts = pipeline.execute()
    detail_logger.debug(f"{npts} points remaining after relaxation dart throwing culling")
    # get the thinned points from the output
    thinned_array = pipeline.arrays[0]
    #
    pts_gdf = gpd.GeoDataFrame(
        thinned_array,
        geometry=gpd.points_from_xy(thinned_array["X"], thinned_array["Y"], crs=crs),
    )
    pts_gdf.to_file(folderpath + "/kriging_pts.gpkg")
    pipeline = pdal.Writer.las(filename=folderpath + "/filtered.laz").pipeline(thinned_array)
    npts = pipeline.execute()
    detail_logger.debug(f"{npts} Points written to output LAZ and geopackage files")

    return pts_gdf


def krige_bathy(krmodel, folderpath, npts, variogram_model, crs):
    """Load the bathymetric points, select a subset of them via PDAL poisson dart-throwing, then krige using pykrige

    Args:
        krmodel (KrigingModel): A kriging model from pykrige
        initial_raster_path (str): path of the starting point raster
        pointfolder_path (_type_): path of the location of the bathymetric points
        npts (integer): number of points to subset from the bathymetric points
    """

    # load the points for kriging
    pts_gdf = prepare_pt_subset_for_kriging(folderpath, npts, crs)

    # open the interpolated raster to get the coordinates
    with rasterio.open(folderpath + "/bilinear.tif") as ras:
        ar = rioxarray.open_rasterio(ras)
        gridx = ar.x.data
        gridy = ar.y.data
    # make sure we are in the same CRS
    assert pts_gdf.crs == ras.crs
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

    detail_logger.debug(
        f"finished kriging, now saving the output raster to {folderpath + 'kalman.tif'}"
    )

    # save the results as a raster with band 1 and the Z value and band 2 as the uncertainty
    with rasterio.open(
        folderpath + "/kriging_output.tif",
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
    detail_logger.debug("Output raster of kriged Z values and uncertainty saved sucessfully")
