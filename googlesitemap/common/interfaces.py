from zope.interface import Interface
from zope.interface import Attribute

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




