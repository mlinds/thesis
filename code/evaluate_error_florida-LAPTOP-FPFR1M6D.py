"""
This script runs the clusting logic on every available beam from florida, and compares the errors with 
"""
import atl03_utils
from glob import iglob


def test_florida(filename, beam):
    """Run a test of a specific pass and beam, and check the error against ground truth florida DEMs

    Args:
        filename (str): path of h5 or netcdf file of a granule
        beam (str): string of a beam name

    Returns:
        dict: dictionary of RMS error against various florida DEMs.
    """
    beamdata = atl03_utils.load_beam_array_ncds(filename, beam)
    if beamdata is None:
        return "Could not open beam"

    point_dataframe = atl03_utils.add_track_dist_meters(beamdata)

    point_dataframe = point_dataframe.bathy.filter_TEP()
    point_dataframe = point_dataframe.bathy.add_sea_level()
    point_dataframe = point_dataframe.bathy.filter_low_points()
    point_dataframe = point_dataframe.bathy.remove_surface_points()
    point_dataframe = atl03_utils.add_dem_data(
        point_dataframe,
        [
            "../data/test_sites/florida_keys/in-situ-DEM/2019_irma.vrt",
            "../data/test_sites/florida_keys/in-situ-DEM/fema_2017.tif",
            "../data/test_sites/florida_keys/GEBCO/gebco.tif",
        ],
    )

    point_dataframe = point_dataframe[point_dataframe["gebco.tif"] > -40]

    if len(point_dataframe) < 10:
        return "Not enough viable points after filtering"
    # point_dataframe = atl03_utils.add_track_dist_meters(point_dataframe.drop(columns=['dist_or']).to_records())

    point_dataframe = atl03_utils.cluster_signal_dbscan(point_dataframe)

    signal_pts = point_dataframe[point_dataframe.SN == "signal"]

    if len(signal_pts) == 0:
        return "no signal found"
    signal_pts = atl03_utils.add_raw_seafloor(signal_pts)

    return atl03_utils.calc_rms_error(
        signal_pts, ["gebco.tif", "2019_irma.vrt", "fema_2017.tif"]
    )


def main():
    ncdf_file_glob = iglob("../data/test_sites/florida_keys/ATL03/*.nc")
    for filename in ncdf_file_glob:
        beams = atl03_utils.get_beams(filename)
        for beam in beams:
            print(
                filename,
                beam,
            )
            print(test_florida(filename, beam))


if __name__ == "__main__":
    main()
