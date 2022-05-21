import numpy as np
from sklearn.cluster import DBSCAN
import pandas as pd
from math import ceil


def cluster_by_chunks(
    point_dataframe: pd.DataFrame,
    Ra: float,
    hscale: float,
    minpts: int,
    chunksize: float,
    chunk_meth: str,
):
    """Run the DBSCAN algorithm by chunks

    Args:
        point_dataframe (pd.DataFrame): dataframe of the photon locations
        Ra (float): Minimum dbscan radius
        hscale (float): How many times to decrease the x scale relative to the z scale
        minpts (int): minimum points per cluster
        chunksize (float): How large to make each chunk (meters for 'dist', number of points for 'points')
        chunk_meth (str): Either 'dist' or 'point'

    Raises:
        ValueError: If the wrong 'chunk_meth' is provided, raises this error

    Returns:
        pd.DataFrame: Dataframe with the signal value added
    """
    total_length = point_dataframe.dist_or.max()
    if chunk_meth == "points":
        # we want chunks of about 10.000 returns
        nchunks = max(round(len(point_dataframe) / chunksize), 1)
    elif chunk_meth == "dist":
        nchunks = ceil(total_length / chunksize)
    else:
        raise ValueError('Chunk method must be "dist" or "points"')

    print(
        f"the total length of the transect being studied is {total_length:.2f}km and {len(point_dataframe)} points"
    )

    # this list will be filled with geodataframes of each chunk
    sndf = []

    print(f"Points will be proccessed in {nchunks} chunks")
    dist_st = 0

    bin_edges = list(
        zip(
            range(0, (nchunks - 1) * chunksize, chunksize),
            range(chunksize, nchunks * chunksize, chunksize),
        )
    )

    print(f"{hscale=}")
    for dist_st, dist_end in bin_edges:
        # print(dist_st,dist_end)
        array = point_dataframe[
            (point_dataframe.dist_or > dist_st) & (point_dataframe.dist_or <= dist_end)
        ].to_records()
        if len(array) < 50:
            continue

        minpts = int(0.03 * len(array))
        print(f"{minpts}")
        V = np.linalg.inv(np.cov(array["dist_or"], array["Z"]))

        fitarray = np.stack([array["dist_or"] / hscale, array["Z"]]).transpose()

        # run the clustering algo
        clustering = DBSCAN(
            eps=Ra,
            min_samples=minpts,
            # metric="mahalanobis",
            # metric_params={"VI": V},
        ).fit(fitarray)

        # add the classes to the DF
        df = pd.DataFrame(array).assign(cluster=clustering.labels_)

        # add readable label
        df["SN"] = df.cluster.apply(lambda x: "noise" if x == -1 else "signal")
        sndf.append(df)

    merged = pd.concat(
        sndf,
    )

    return merged
