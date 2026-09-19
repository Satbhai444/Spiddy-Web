"""
SpiddyWeb Views Package.

This re-exports all views so that `drop/urls.py` can still do:
`from . import views` and access `views.upload_view` etc without breaking anything during migration.
"""

from .filedrop import *
from .pages import *
from .pwa import *
from .rooms import *
from .seo import *
