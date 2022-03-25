FROM mambaorg/micromamba:0.22.0
RUN micromamba install --yes --name base --channel conda-forge \
    jupyter     \
    jupyterlab \
    numpy \
    pandas \
    scipy \
    Pillow \
    matplotlib \
    folium \
    fiona \
    shapely \
    geopandas \
    rasterio \
    tifffile \
    geemap \
    sentinelhub \
    sentinelsat \ 
    xarray \
    dask \
    netCDF4 \
    bottleneck \
    h5netcdf \
    dask \
    whitebox && \
    micromamba clean --all --yes