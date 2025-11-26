from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu, QApplication
from netCDF4 import Dataset, num2date
import numpy.ma as ma
import numpy as np

import utils

LON_NAMES = {"lon", "longitude", "LONGITUDE", "LON", "x", "X"}
LAT_NAMES = {"lat", "latitude", "LATITUDE", "LAT", "y", "Y"}
TIME_NAMES = {"time", "Time", "T", "valid_time", "date"}


def get_shape_info_from_ncfile(ncfile, variable_name):
    variable_shape = ncfile.variables[variable_name].shape
    num_dimensions = len(variable_shape)

    drop_dim_indices = []
    if num_dimensions > 1:
        for i in range(num_dimensions):
            dim_length = variable_shape[i]
            if dim_length == 1 or dim_length == 0:
                drop_dim_indices.append(i)

    return variable_shape, num_dimensions, drop_dim_indices

def get_shape_info(file_path, variable_name):
    ncfile = Dataset(file_path, "r")
    variable_shape, num_dimensions, drop_dim_indices = get_shape_info_from_ncfile(ncfile, variable_name)
    ncfile.close()

    return variable_shape, num_dimensions, drop_dim_indices


def identify_dims_from_vardata(dims, shapes):
    sizes = {d: s for d, s in zip(dims, shapes)}

    # identify dims to be dropped
    drop_dims = []
    for d, s in sizes.items():
        if s < 2 and (s != 1 or len(shapes) != 1):
            drop_dims.append(d)

    # all dims that are not dropped are candidates for x and y dims
    candidate_dims = [d for d in dims if d not in drop_dims]

    # try to identify coordinates by name
    x_candidates = [d for d in candidate_dims if d in LON_NAMES]
    y_candidates = [d for d in candidate_dims if d in LAT_NAMES]
    t_candidates = [d for d in candidate_dims if d in TIME_NAMES]
    x_dim = x_candidates[0] if x_candidates else None
    y_dim = y_candidates[0] if y_candidates else None
    t_dim = t_candidates[0] if t_candidates else None

    sliceable_dims = [d for d in dims if d not in (drop_dims + [x_dim, y_dim])]

    return {
        "x_dim": x_dim,
        "y_dim": y_dim,
        "t_dim": t_dim,
        "drop_dims": drop_dims,
        "sliceable_dims": sliceable_dims,
        "all_dims": dims,
        "sizes": sizes,
        "can_plot": bool(x_dim and y_dim),
        "can_slice": bool((len(dims) - len(drop_dims)) > 2)
    }

def identify_dims(file_path, variable_name):
    ncfile = Dataset(file_path, "r")
    var = ncfile.variables[variable_name]
    dims = list(var.dimensions)
    shapes = list(var.shape)

    var_props = identify_dims_from_vardata(dims, shapes)

    var_props["file_path"] = file_path
    var_props["variable_name"] = variable_name
    var_props["fill_value"] = var.get_fill_value()

    ncfile.close()

    return var_props

def slice_timeseries(var_props, slice_indices, x_index, y_index, chosen_dim_name):
    ncfile = Dataset(var_props["file_path"], "r")
    vardata = ncfile.variables[var_props["variable_name"]]

    # build slices covering all dims in var order
    slices = []
    for i in range(len(var_props["all_dims"])):  # I am so sorry to anyone reading this
        d = var_props["all_dims"][i]
        if d not in var_props["drop_dims"]:
            if d == var_props["x_dim"]:
                slices.append(x_index)
            elif d == var_props["y_dim"]:
                slices.append(y_index)
            elif d == chosen_dim_name:
                slices.append(slice(None))
            else:
                slices.append(slice_indices[i])
        else:
            slices.append(0)

    timeseries = vardata[tuple(slices)]

    ncfile.close()

    return timeseries

def slice_data(var_props, slice_indices, vardata):
    if vardata.shape == (1,):
        return vardata[:]

    # build slices covering all dims in var order
    slices = []
    for i in range(len(var_props["all_dims"])): # I am so sorry to anyone reading this
        d = var_props["all_dims"][i]
        if d not in var_props["drop_dims"]:
            if d == var_props["x_dim"] or d == var_props["y_dim"]:
                slices.append(slice(None))
            else:
                if d not in var_props["sliceable_dims"] or var_props["can_slice"]:
                    slices.append(slice_indices[i])
        else:
            slices.append(0)

    plotdata = vardata[tuple(slices)]

    # mask the data with the fill value from netcdf file
    return ma.masked_equal(plotdata, var_props["fill_value"])


def get_initial_data(var_props):
    ncfile = Dataset(var_props["file_path"], "r")

    vardata = ncfile.variables[var_props["variable_name"]]

    xdata, ydata = None, None
    try:
        xdata = ncfile.variables[var_props["x_dim"]][:]
        ydata = ncfile.variables[var_props["y_dim"]][:]
    except:
        pass

    xdataunit = None
    try:
        xdataunit = ncfile.variables[var_props["x_dim"]].units
    except Exception:
        pass

    ydataunit = None
    try:
        ydataunit = ncfile.variables[var_props["y_dim"]].units
    except Exception:
        pass

    slicedata = []
    slicecalendar = []
    slicetunits = []
    timesliceindex = 0

    if var_props["can_slice"]:
        for i in range(len(var_props["sliceable_dims"])):
            slice_dim = var_props["sliceable_dims"][i]
            slice_variable = ncfile.variables[slice_dim]

            slicedata.append(slice_variable[:])

            calendar = None
            try:
                calendar = slice_variable.calendar
            except Exception:
                pass
            slicecalendar.append(calendar)

            tunits = None
            try:
                tunits = slice_variable.units
            except Exception:
                pass
            slicetunits.append(tunits)

            if slice_dim == var_props["t_dim"]:
                timesliceindex = i

    variable_units = None
    try:
        variable_units = vardata.units
    except Exception:
        pass

    variable_calendar = None
    try:
        variable_calendar = vardata.calendar
    except Exception:
        pass

    variable_description = None
    try:
        variable_description = vardata.description
    except Exception:
        pass

    if xdata is not None and ydata is not None:
        xboundaries, yboundaries = utils.grid_boundaries_from_centers(xdata, ydata)
    else:
        xboundaries, yboundaries = None, None

    sliced_data = slice_data(var_props, [0 for _ in range(len(var_props["sliceable_dims"]))], vardata)

    ncfile.close()

    return slicedata, slicecalendar, slicetunits, timesliceindex, variable_units, variable_calendar, variable_description, xboundaries, yboundaries, sliced_data, xdata, ydata, xdataunit, ydataunit

def get_sliced_data(var_props, slice_indices):
    ncfile = Dataset(var_props["file_path"], "r")
    vardata = ncfile.variables[var_props["variable_name"]]
    sliced_data = slice_data(var_props, slice_indices, vardata)
    ncfile.close()
    return sliced_data