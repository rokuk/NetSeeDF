import urllib.parse
from threading import Lock, Thread

from flask import Flask, send_file, request
from io import BytesIO
import xarray as xr
import numpy as np
from pyproj import Transformer
import datashader as ds
import datashader.transfer_functions as tf
import matplotlib as mpl
from waitress import serve
import queue

app = Flask(__name__)

task_queue = queue.Queue()
lock = Lock()

def worker():
    while True:
        task = task_queue.get()
        if task is None:  # Exit signal
            break
        try:
            with lock:
                img_buffer = process_image_request(*task['args'])
                task['result'].put(img_buffer)
        except Exception as e:
            print(e)
        finally:
            task_queue.task_done()

thread = Thread(target=worker, daemon=True)
thread.start()

@app.route('/image', methods=['GET'])
def generate_image():
    result_queue = queue.Queue()
    args = request.args

    task_queue.put({
        'args': (args.get('filepath'), args.get('varname'), args.get('tslice'), args.get('tname'), args.get('xname'), args.get('yname'), args.get('projstr'), args.get('vmin'), args.get('vmax')),
        'result': result_queue
    })

    img_buffer = result_queue.get()

    return send_file(img_buffer, mimetype='image/png')

def process_image_request(filepath, varname, tslice, tname, xname, yname, projstr, vmin, vmax):
    filepath = urllib.parse.unquote(filepath)
    varname = urllib.parse.unquote(varname)
    tslice = int(urllib.parse.unquote(tslice))
    tname = urllib.parse.unquote(tname)
    xname = urllib.parse.unquote(xname)
    yname = urllib.parse.unquote(yname)
    projstr = urllib.parse.unquote(projstr)
    vminparam = urllib.parse.unquote(vmin)
    vmaxparam = urllib.parse.unquote(vmax)

    if vminparam != "None":
        vmin = float(vminparam)
    else:
        vmin = None

    if vmaxparam != "None":
        vmax = float(vmaxparam)
    else:
        vmax = None

    with xr.open_dataset(filepath, mask_and_scale=True) as ds_nc:
        var2d = ds_nc[varname].isel({tname: tslice})

    lons, lats = var2d[xname].values, var2d[yname].values
    xmin, ymin, xmax, ymax = np.min(lons), np.min(lats), np.max(lons), np.max(lats)
    ymin = max(ymin, -85)
    ymax = min(ymax, 85)

    transformer = Transformer.from_crs(projstr, "EPSG:3857", always_xy=True)
    xmesh, ymesh = np.meshgrid(lons, lats)
    xdata_3857, ydata_3857 = transformer.transform(xmesh, ymesh)

    _, ymin_proj = transformer.transform(0, ymin)
    _, ymax_proj = transformer.transform(0, ymax)

    canvas = ds.Canvas(plot_width=var2d.shape[0], plot_height=var2d.shape[1],
                       x_range=[np.min(xdata_3857), np.max(xdata_3857)], y_range=[ymin_proj, ymax_proj])

    da = xr.DataArray(var2d, name='Z', dims=['y', 'x'],
                      coords={'Qy': (['y', 'x'], ydata_3857),
                              'Qx': (['y', 'x'], xdata_3857)})

    agg = canvas.quadmesh(da, x='Qx', y='Qy')

    if vmin is not None or vmax is not None:
        agg = agg.clip(vmin, vmax)

    img = tf.shade(agg, cmap=mpl.cm.inferno, how="linear")

    img_buffer = BytesIO()
    img.to_pil().save(img_buffer, 'PNG')
    img_buffer.seek(0)

    return img_buffer

def start_server():
    serve(app, host='127.0.0.1', port=33764)
