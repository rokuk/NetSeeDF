import numpy as np

# Copyright (C) 2013-, Folium developers
# See https://github.com/python-visualization/folium/graphs/contributors for a
# full list of contributors.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
def mercator_transform(data, lat_min, lat_max):
    """
    Transforms an image computed in (longitude,latitude) coordinates into
    a Mercator projection image.

    Parameters
    ----------

    data: numpy array or equivalent list-like object.
        Must be NxM (mono).

    lat_bounds : length 2 tuple
        Minimal and maximal value of the latitude of the image.
        Bounds must be between -85.051128779806589 and 85.051128779806589
        otherwise they will be clipped to that values.
    """

    def mercator(x):
        return np.arcsinh(np.tan(x * np.pi / 180.0)) * 180.0 / np.pi

    array = data.copy()
    height, width = array.shape

    lat_min = max(lat_min, -85.051128779806589)
    lat_max = min(lat_max, 85.051128779806589)

    array = array[::-1, :]

    lats = lat_min + np.linspace(0.5 / height, 1.0 - 0.5 / height, height) * (
            lat_max - lat_min
    )
    latslats = mercator(lat_min) + np.linspace(
        0.5 / height, 1.0 - 0.5 / height, height
    ) * (mercator(lat_max) - mercator(lat_min))

    out = np.zeros((height, width))
    for i in range(width):
        out[:, i] = np.interp(latslats, mercator(lats), array[:, i])

    return out[::-1, :], latslats
