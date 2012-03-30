# Authors: Davide Moro <davide.moro@redomino.com> and contributors (see docs/CONTRIBUTORS.txt)
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.

from zope.interface import Interface
from zope.interface import Attribute

class ISitemapLayer(Interface):
    """ Layer interface """

class ISiteMapView(Interface):
    """ Sitemap view """

    template = Attribute("""Template used for sitemap generation""")
    indextemplate = Attribute("""Template used for sitemap indexes""")

    maxlen = Attribute("""The maximum number of items for sitemap""")
    query_dict = Attribute("""The catalog query used for get sitemap elements""")
    filename = Attribute("""The generated sitemap's filename""")
    enable_sitemap = Attribute("""Sitemap generation available only if enable_sitemap is enabled""")

    def sitemaps():
        """Get sitemaps data when using indexes of sitemaps"""

    def getStartEnd():
        """ Get window slice of brains used for indexes of sitemaps"""

    def objects():
        """Returns the data to create the sitemap. It may be a portion of all existing objects when we need to
           generate sitemap indexes.
        """

    def generate():
        """ Generates the cached Gzipped sitemap.
            You can just override this method for change caching policy (different kind of sitemaps may have
            different settings).
        """

    def __call__():
        """Checks if the sitemap feature is enabled and returns it.
           It may returns a standard sitemap or an index of sitemaps when where are more than maxlen objects
           on our site.
        """




