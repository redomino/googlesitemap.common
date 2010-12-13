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
        self.sitemap = getMultiAdapter((self.portal, self.portal.REQUEST),
                                       name='sitemap.xml.gz')
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
        self.logout()
        
    def uncompress(self, sitemapdata):
        sio = StringIO(sitemapdata)
        unziped = GzipFile(fileobj=sio)
        xml = unziped.read()
        unziped.close()
        return xml

    def test_view(self):
        """ If the sitemap class is right """
        from googlesitemap.common.sitemap import SiteMapCommonView
        sitemap_view = self.portal.restrictedTraverse('@@sitemap.xml.gz')
        self.assertTrue(isinstance(sitemap_view, SiteMapCommonView))

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


def test_suite():
    from unittest import defaultTestLoader
    return defaultTestLoader.loadTestsFromName(__name__)
