from branca.element import Element, CssLink
from jinja2 import Template
import os


class Link(Element):
    def get_code(self):
        if self.code is None:
            with open(appcontext.get_resource(self.url), "r", encoding="utf-8") as f:
                contents = f.read()
            self.code = contents
        return self.code

    def to_dict(self, depth=-1, **kwargs):
        out = super(Link, self).to_dict(depth=-1, **kwargs)
        out["url"] = self.url
        return out


class JavascriptLink(Link):

    _template = Template("<script>{{this.get_code()}}</script>")

    def __init__(self, url, download=False):
        super(JavascriptLink, self).__init__()
        self._name = "JavascriptLink"
        self.url = url
        self.code = None


class CssLink(Link):
    _template = Template("<style>{{this.get_code()}}</style>")

    def __init__(self, url, download=False):
        super(CssLink, self).__init__()
        self._name = "CssLink"
        self.url = url
        self.code = None

def set_appcontext(appctxt):
    global appcontext
    appcontext = appctxt

def setup_folium():
    import folium

    folium.folium._default_js = [
        (name, os.path.join("offline_folium", os.path.basename(url)))
        for (name, url) in folium.folium._default_js
    ]
    folium.folium._default_css = [
        (name, os.path.join("offline_folium", os.path.basename(url)))
        for (name, url) in folium.folium._default_css
    ]
    folium.Map.default_js = folium.folium._default_js
    folium.Map.default_css = folium.folium._default_css

    folium.elements.JavascriptLink = JavascriptLink
    folium.elements.CssLink = CssLink