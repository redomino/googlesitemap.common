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
from Products.Five.testbrowser import Browser
from urllib2 import HTTPError

from Products.CMFCore.utils import getToolByName

from googlesitemap.common.tests.base import FunctionalTestCase

class SiteMapIndexTestCase(FunctionalTestCase):
    """base test case with convenience methods for testing the sitemap index"""

    def afterSetUp(self):
        super(SiteMapIndexTestCase, self).afterSetUp()

        self.sitemap = getMultiAdapter((self.portal, self.portal.REQUEST),
                                       name='sitemapindex.xml.gz')
        self.wftool = getToolByName(self.portal, 'portal_workflow')

        
        self.portal.manage_delObjects()

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

        #Change maxlen
        from googlesitemap.common import config
        config.MAXLEN = 5

        self.loginAsPortalOwner()

        self.logout()
        self.browser = Browser()


    def uncompress(self, sitemapdata):
        sio = StringIO(sitemapdata)
        unziped = GzipFile(fileobj=sio)
        xml = unziped.read()
        unziped.close()
        return xml

    def test_maxlen(self):
        self.assertTrue(5 == self.sitemap.maxlen)

    def test_link(self):
        xml = self.uncompress(self.sitemap())
        self.assertTrue('?index=0' in xml)
        self.assertTrue('?index=1' in xml)
        self.assertTrue('?index=2' not in xml)

    def test_indextags(self):
        xml = self.uncompress(self.sitemap())
        self.assertTrue('<sitemapindex' in xml)
        self.assertTrue('<sitemap' in xml)
        self.assertTrue('<lastmod' in xml)

    def test_open_fail(self):
        self.loginAsAdmin()
        browser = self.browser
        self.assertRaises(HTTPError, browser.open, 'http://nohost/plone/sitemapindex.xml.gz?index=2')

    def test_open(self):
        self.loginAsAdmin()
        browser = self.browser
        browser.open('http://nohost/plone/sitemapindex.xml.gz?index=1')
        xml = self.uncompress(browser.contents)


    def loginAsAdmin(self):
        """ Perform through-the-web login.

        Simulate going to the login form and logging in.

        We use username and password provided by PloneTestCase.

        This sets session cookie for testbrowser.
        """
        from Products.PloneTestCase.setup import portal_owner, default_password

        # Go admin
        browser = self.browser
        browser.open(self.portal.absolute_url() + "/login_form")
        browser.getControl(name='__ac_name').value = portal_owner
        browser.getControl(name='__ac_password').value = default_password
        browser.getControl(name='submit').click()


def test_suite():
    from unittest import defaultTestLoader
    return defaultTestLoader.loadTestsFromName(__name__)
