FROM jupyter/scipy-notebook
RUN mamba install --yes --name base --channel conda-forge \
    jupyter     \
    jupyterlab \
    icepyx \
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
    cfgrib \
    whitebox && \
    mamba clean --all --yes