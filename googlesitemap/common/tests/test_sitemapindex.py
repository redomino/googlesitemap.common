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
                                       name='sitemapindex.xml.gz')
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

# TODO


def test_suite():
    from unittest import defaultTestLoader
    return defaultTestLoader.loadTestsFromName(__name__)
