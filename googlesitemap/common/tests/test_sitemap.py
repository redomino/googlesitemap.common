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
from StringIO import StringIO

from zope.component import getMultiAdapter
from zope.publisher.interfaces import INotFound

from Products.CMFCore.utils import getToolByName

from googlesitemap.common.tests.base import TestCase


class SiteMapTestCase(TestCase):
    """base test case with convenience methods for all sitemap tests"""

    def afterSetUp(self):
        super(SiteMapTestCase, self).afterSetUp()
        self.wftool = getToolByName(self.portal, 'portal_workflow')

        # we need to explizitly set a workflow cause we can't rely on the
        # test environment.
        # `instance test -m plone.app.layout`:
        # wftool._default_chain == 'simple_publication_workflow'
        # `instance test -m plone.app`:
        # wftool._default_chain == 'plone_workflow'
        self.wftool.setChainForPortalTypes(['Document'],
                                           'simple_publication_workflow')

        self.site_properties = getToolByName(
            self.portal, 'portal_properties').site_properties
        self.site_properties.manage_changeProperties(enable_sitemap=True)

        #setup private content that isn't accessible for anonymous
        self.loginAsPortalOwner()
        self.portal.invokeFactory(id='private', type_name='Document')
        private = self.portal.private
        self.assertTrue('private' == self.wftool.getInfoFor(private,
                                                            'review_state'))
        
        #setup published content that is accessible for anonymous
        self.portal.invokeFactory(id='published', type_name='Document')
        published = self.portal.published
        self.wftool.doActionFor(published, 'publish')
        self.assertTrue('published' == self.wftool.getInfoFor(published,
                                                              'review_state'))

        #setup pending content that is accessible for anonymous
        self.portal.invokeFactory(id='pending', type_name='Document')
        pending = self.portal.pending
        self.wftool.doActionFor(pending, 'submit')
        self.assertTrue('pending' == self.wftool.getInfoFor(pending,
                                                            'review_state'))

        self.portal.invokeFactory(id='file1', type_name='File')
        self.file1 = self.portal.file1
        self.portal.invokeFactory(id='image1', type_name='Image')
        self.image1 = self.portal.image1

        self.logout()

    @property
    def sitemap(self):
        return getMultiAdapter((self.portal, self.portal.REQUEST),
                               name='sitemapindex.xml.gz')
        
    def uncompress(self, sitemapdata):
        sio = StringIO(sitemapdata)
        unziped = GzipFile(fileobj=sio)
        xml = unziped.read()
        unziped.close()
        return xml

    def test_layers(self):
        """ Browser layers setup """
        from googlesitemap.common.interfaces import ISitemapLayer

        from plone.browserlayer.utils import registered_layers
        # our layer is correctly applied
        self.assertTrue(ISitemapLayer in registered_layers())

    def test_view(self):
        """ If the sitemap class is right """
        from googlesitemap.common.sitemap import SiteMapCommonView
        # this test fails, we need to fix the tests setup
        # I've created a fake testing.zcml to fix this
        self.assertTrue(isinstance(self.sitemap, SiteMapCommonView))

    def test_disabled(self):
        '''
        If the sitemap is disabled throws a 404 error.
        '''
        self.site_properties.manage_changeProperties(enable_sitemap=False)
        try:
            self.sitemap()
        except Exception, e:
            # zope2 and repoze.zope2 use different publishers and raise
            # different exceptions. but both implement INotFound.
            self.assertTrue(INotFound.providedBy(e))
        else:
            self.fail('The disabled sitemap view has to raise NotFound!')
            
    def test_authenticated_before_anonymous(self):
        '''
        Requests for the sitemap by authenticated users are not cached.
        anomymous users get a uncached sitemap that only contains content
        that they are supposed to see.
        '''

        # first round as an authenticated (manager)
        self.loginAsPortalOwner()
        xml = self.uncompress(self.sitemap())
        self.assertTrue('<loc>http://nohost/plone/private</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/pending</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/published</loc>' in xml)

        # second round as anonymous
        self.logout()
        xml = self.uncompress(self.sitemap())
        self.assertFalse('<loc>http://nohost/plone/private</loc>' in xml)
        self.assertFalse('<loc>http://nohost/plone/pending</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/published</loc>' in xml)

    def test_anonymous_before_authenticated(self):
        '''
        Requests for the sitemap by anonymous users are cached.
        authenticated users get a uncached sitemap. Test that the cached
        Sitemap is not delivered to authenticated users.
        '''

        # first round as anonymous
        xml = self.uncompress(self.sitemap())
        self.assertFalse('<loc>http://nohost/plone/private</loc>' in xml)
        self.assertFalse('<loc>http://nohost/plone/pending</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/published</loc>' in xml)

        # second round as an authenticated (manager)
        self.loginAsPortalOwner()
        xml = self.uncompress(self.sitemap())
        self.assertTrue('<loc>http://nohost/plone/private</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/pending</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/published</loc>' in xml)

    def test_changed_catalog(self):
        '''
        The sitemap is generated from the catalog. If the catalog changes, a new
        sitemap has to be generated.
        '''

        xml = self.uncompress(self.sitemap())
        self.assertFalse('<loc>http://nohost/plone/pending</loc>' in xml)

        # changing the workflow state 
        self.loginAsPortalOwner()
        pending = self.portal.pending
        self.wftool.doActionFor(pending, 'publish')
        self.logout()

        xml = self.uncompress(self.sitemap())
        self.assertTrue('<loc>http://nohost/plone/pending</loc>' in xml)

        #removing content
        self.loginAsPortalOwner()
        self.portal.manage_delObjects(['published',])
        self.logout()

        xml = self.uncompress(self.sitemap())
        self.assertFalse('<loc>http://nohost/plone/published</loc>' in xml)        

    def test_image_file(self):
        """ Image and files are handled correctly? """
        xml = self.uncompress(self.sitemap())
        self.assertTrue(self.image1.absolute_url() in xml)
        self.assertTrue(self.file1.absolute_url() in xml)

        # both file and file/view in sitemap
        file_url = self.file1.absolute_url()
        self.assertTrue('<loc>%s</loc>' % file_url in xml)
        self.assertTrue('<loc>%s/view</loc>' % file_url in xml)

        # plain images should not be included in sitemaps, use sitemap for images!
        image_url = self.image1.absolute_url()
        self.assertFalse('<loc>%s</loc>' % image_url in xml)
        self.assertTrue('<loc>%s/view</loc>' % image_url in xml)

    def test_lastmod(self):
        """ 
            Seems to be better having spaces in lastmod.
            It is undocumented but it seems better this format
              <lastmod> DATE </lastmod>  
            instead of:
              <lastmod>DATE</lastmod>  

            DATE should be in ZULU time format ('2010-12-14T10:53:21Z')
        """
        xml = self.uncompress(self.sitemap())
        zulu_time = self.image1.modified().HTML4()
        self.assertTrue('<lastmod> %s </lastmod>' % zulu_time in xml)
        self.assertFalse('<lastmod>%s</lastmod>' % zulu_time in xml)


def test_suite():
    from unittest import defaultTestLoader
    return defaultTestLoader.loadTestsFromName(__name__)
