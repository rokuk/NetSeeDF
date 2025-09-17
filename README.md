# NetSeeDF

NetSeeDF is a simple, lightweight tool for exploring and visualizing data in NetCDF files.

Inspired by [Panoply](https://www.giss.nasa.gov/tools/panoply/), NetSeeDF is designed to be simpler and more limited tool that does **not** require a Java installation. Designed with students and researchers in mind, it lets you quickly explore available variables, their shapes, and visualize grid point locations on a map.

NetSeeDf is developed by Rok Kuk [rokuk.org](https://rokuk.org)

![Main window](https://storage.rokuk.org/netseedf/foto1.png)

|![Data display](https://storage.rokuk.org/netseedf/foto2.png)|![Map](https://storage.rokuk.org/netseedf/foto3.png)|
|:-:|:-:|

## Features
- List variables in a NetCDF file. 
- View variable values in a table (supports 1D, 2D, and 3D variables)
- Visualize gridded variable values on an interactive map (supports slicing 3D variables, e.g. in time)

## Limitations
- The software is still in development and currently supports only a limited number of NetCDF file structures.
- Limited coordinate systems are implemented. Rotated pole grid (rlat, rlon) and grid reference systems (easting, northing) are not supported yet.
- Only 3D variables can be plotted on a map
- Showing map background (OpenStreetMap tiles) requires an internet connection

## Development
NetSeeDF is written in Python 3.13
- Install the required packages in `requirements.txt`
- To make the map work offline, install the package `offline_folium` and run `python -m offline_folium` when online. If needed, change the path where `offline_folium` files were downloaded in [netseedf.spec](netseedf.spec)
- Build the app with `pyinstaller netseedf.spec`
