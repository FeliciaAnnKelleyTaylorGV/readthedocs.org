from contextlib import contextmanager
from unittest import mock

import django_dynamic_fixture as fixture
import docutils
import pytest
import sphinx
from django.core.cache import cache
from django.urls import reverse
from packaging.version import Version

from readthedocs.projects.models import Project

from .utils import srcdir


@pytest.mark.django_db
@pytest.mark.embed_api
class TestEmbedAPIv3InternalPages:

    @pytest.fixture(autouse=True)
    def setup_method(self, settings):
        settings.USE_SUBDOMAIN = True
        settings.PUBLIC_DOMAIN = 'readthedocs.io'
        settings.RTD_EMBED_API_EXTERNAL_DOMAINS = []

        self.api_url = reverse('embed_api_v3')

        self.project = fixture.get(
            Project,
            slug='project'
        )

        yield
        cache.clear()

    def _mock_open(self, content):
        @contextmanager
        def f(*args, **kwargs):
            read_mock = mock.MagicMock()
            read_mock.read.return_value = content
            yield read_mock
        return f

    @pytest.mark.sphinx("html", srcdir=srcdir, freshenv=True)
    @mock.patch("readthedocs.embed.v3.views.build_media_storage.open")
    @mock.patch("readthedocs.embed.v3.views.build_media_storage.exists")
    def test_default_main_section(self, storage_exists, storage_open, app, client):
        app.build()
        path = app.outdir / 'index.html'
        assert path.exists() is True
        content = open(path).read()

        storage_exists.return_value = True
        storage_open.side_effect = self._mock_open(content)

        params = {
            'url': 'https://project.readthedocs.io/en/latest/',
        }
        response = client.get(self.api_url, params)
        assert response.status_code == 200

        # https://github.com/sphinx-doc/sphinx/commit/bc635627d32b52e8e1381f23cddecf26429db1ae
        if sphinx.version_info < (5, 0, 0):
            title = "Permalink to this headline"
        else:
            title = "Permalink to this heading"

        # Note the difference between `<section>` and `<div class="section">`
        if Version(docutils.__version__) >= Version('0.17'):
            content = f'<div class="body" role="main">\n            \n  <section id="title">\n<h1>Title<a class="headerlink" href="https://project.readthedocs.io/en/latest/#title" title="{title}">¶</a></h1>\n<p>This is an example page used to test EmbedAPI parsing features.</p>\n<section id="sub-title">\n<h2>Sub-title<a class="headerlink" href="https://project.readthedocs.io/en/latest/#sub-title" title="{title}">¶</a></h2>\n<p>This is a reference to <a class="reference internal" href="https://project.readthedocs.io/en/latest/#sub-title"><span class="std std-ref">Sub-title</span></a>.</p>\n</section>\n<section id="manual-reference-section">\n<span id="manual-reference"></span><h2>Manual Reference Section<a class="headerlink" href="https://project.readthedocs.io/en/latest/#manual-reference-section" title="{title}">¶</a></h2>\n<p>This is a reference to a manual reference <a class="reference internal" href="https://project.readthedocs.io/en/latest/#manual-reference"><span class="std std-ref">Manual Reference Section</span></a>.</p>\n</section>\n</section>\n\n\n          </div>'
        else:
            content = f'<div class="body" role="main">\n            \n  <div class="section" id="title">\n<h1>Title<a class="headerlink" href="https://project.readthedocs.io/en/latest/#title" title="{title}">¶</a></h1>\n<p>This is an example page used to test EmbedAPI parsing features.</p>\n<div class="section" id="sub-title">\n<h2>Sub-title<a class="headerlink" href="https://project.readthedocs.io/en/latest/#sub-title" title="{title}">¶</a></h2>\n<p>This is a reference to <a class="reference internal" href="https://project.readthedocs.io/en/latest/#sub-title"><span class="std std-ref">Sub-title</span></a>.</p>\n</div>\n<div class="section" id="manual-reference-section">\n<span id="manual-reference"></span><h2>Manual Reference Section<a class="headerlink" href="https://project.readthedocs.io/en/latest/#manual-reference-section" title="{title}">¶</a></h2>\n<p>This is a reference to a manual reference <a class="reference internal" href="https://project.readthedocs.io/en/latest/#manual-reference"><span class="std std-ref">Manual Reference Section</span></a>.</p>\n</div>\n</div>\n\n\n          </div>'

        assert response.json() == {
            'url': 'https://project.readthedocs.io/en/latest/',
            'fragment': None,
            'content': content,
            'external': False,
        }

    @pytest.mark.sphinx("html", srcdir=srcdir, freshenv=False)
    @mock.patch("readthedocs.embed.v3.views.build_media_storage.open")
    @mock.patch("readthedocs.embed.v3.views.build_media_storage.exists")
    def test_s3_storage_decoded_filename(
        self, storage_exists, storage_open, app, client
    ):
        storage_exists.return_value = True
        storage_open.side_effect = self._mock_open('<div id="section">content</div>')

        params = {
            "url": "https://project.readthedocs.io/en/latest/My%20Spaced%20File.html#section",
        }
        response = client.get(self.api_url, params)
        assert response.status_code == 200

        storage_open.assert_called_once_with("html/project/latest/My Spaced File.html")
