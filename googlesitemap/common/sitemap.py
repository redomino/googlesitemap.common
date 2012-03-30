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

from gzip import GzipFile
from cStringIO import StringIO

from DateTime import DateTime
from zope.interface import implements
from zope.component import getMultiAdapter
from zope.publisher.interfaces import NotFound

from plone.memoize import ram
from plone.memoize.instance import memoize

from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName

from googlesitemap.common.interfaces import ISiteMapView
from googlesitemap.common import config


def _render_defaultcachekey(fun, self):
    # Cache by filename
    mtool = getToolByName(self.context, 'portal_membership')
    if not mtool.isAnonymousUser():
        raise ram.DontCache

    url_tool = getToolByName(self.context, 'portal_url')
    catalog = getToolByName(self.context, 'portal_catalog')
    counter = catalog.getCounter()
    return '%s/%s/%s/%s' % (url_tool(), self.filename, counter, str(self.index))


class SiteMapCommonView(BrowserView):
    """ Base class for build Sitemaps """
    implements(ISiteMapView)

    template = ViewPageTemplateFile('sitemap.xml')
    indextemplate = ViewPageTemplateFile('sitemapindex.xml')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.index = getattr(self.request, 'index', None)

    @property
    def maxlen(self):
        return config.MAXLEN

    @property
    def query_dict(self):
        return {'Language': 'all', 
                'sort_on': 'Date',
                'sort_order':'reverse',
               }

    @property
    def filename(self):
        return 'sitemap.xml'

    @property
    def enable_sitemap(self):
        sp = getToolByName(self.context, 'portal_properties').site_properties
        return sp.enable_sitemap

    @memoize
    def portal_url(self):
        return getMultiAdapter((self.context, self.request), name=u"plone_portal_state").portal_url()

    def sitemaps(self):
        """ Get sitemaps data when using indexes of sitemaps """
        for current in enumerate(self._catalogbrains()[0::self.maxlen]):
            index = current[0]
            item = current[1]
           
            maxdate = DateTime(item.Date).ISO8601()
            url = '%s/%s?index=%d' % (self.portal_url(), self.filename, index)
            yield {'maxdate':maxdate, 'url':url}

# TODO: re-enable memoize without breaking tests
#    @memoize
    def _catalogbrains(self):
        """Returns the data to create the sitemap. Max items = 1000 * maxlen using sitemap indexes.
           maxlen depends on the specific sitemap (standard sitemap, video, news, etc).
        """
        catalog = getToolByName(self.context, 'portal_catalog')
        return catalog.searchResults(**self.query_dict)[:self.maxlen*1000]

    def getStartEnd(self):
        """ Get window slice of brains """
        start = None
        end = None
        if self.index is not None:
            start = int(self.index)*self.maxlen
            end = start + self.maxlen
        return (start, end)

    def _slicecatalogbrains(self):
        """ Get the right window of brains """
        start, end = self.getStartEnd()
        if start is not None and end is not None:
            catalog_brains = self._catalogbrains()[start:end]
        else:
            catalog_brains = self._catalogbrains()
        return catalog_brains


    def objects(self):
        """Returns the data to create the sitemap."""
        catalog_brains = self._slicecatalogbrains()

        for item in catalog_brains:
            if item.portal_type in ['Image']:
                yield {
                    'loc': '%s/view' % item.getURL(),
                    'lastmod': item.modified.HTML4(),
                    #'changefreq': 'always', # hourly/daily/weekly/monthly/yearly/never
                    #'prioriy': 0.5, # 0.0 to 1.0
                }
            else:
                if item.portal_type in ['File']:
                    yield {
                        'loc': '%s/view' % item.getURL(),
                        'lastmod': item.modified.HTML4(),
                        #'changefreq': 'always', # hourly/daily/weekly/monthly/yearly/never
                        #'prioriy': 0.5, # 0.0 to 1.0
                    }
                yield {
                    'loc': item.getURL(),
                    'lastmod': item.modified.HTML4(),
                    #'changefreq': 'always', # hourly/daily/weekly/monthly/yearly/never
                    #'prioriy': 0.5, # 0.0 to 1.0
                }

    def _uncachedgenerate(self):
        """ Generates the Gzipped sitemap uncached data """
        len_brains = len(self._catalogbrains())

        if self.index is None:
            # no index specified in the url
            if len_brains < self.maxlen:
                # ok, we have few items, let's generate the standard sitemap
                xml = self.template()
            else:
                # a lot of items, let's generate a sitemap index
                xml = self.indextemplate()
        elif int(self.index)*self.maxlen >= len_brains:
            # bad index specified
            raise NotFound(self.context, '%s-%s' % (self.index, self.filename), self.request)
        else:
            # index specified in the url
            xml = self.template()

        if self.index is not None:
            filename = "%s-%s" % (self.index, self.filename)
        else:
            filename = self.filename

        fp = StringIO()
        gzip = GzipFile(filename, 'w', 9, fp)
        gzip.write(xml)
        gzip.close()
        data = fp.getvalue()
        fp.close()
        return data

    @ram.cache(_render_defaultcachekey)
    def generate(self):
        """ Generates the cached Gzipped sitemap.
            Override just this method for change caching policy
        """
        return self._uncachedgenerate()

    def __call__(self):
        """Checks if the sitemap feature is enabled and returns it."""
        if not self.enable_sitemap:
            # sitemap enabled
            raise NotFound(self.context, '%s' % self.filename, self.request)

        self.request.response.setHeader('Content-Type',
                                        'application/octet-stream')
        return self.generate()


