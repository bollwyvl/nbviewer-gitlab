#-----------------------------------------------------------------------------
#  Copyright (C) 2013 The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

import json
import mimetypes

from tornado import (
    web,
    gen,
)
from tornado.log import app_log

from nbviewer.providers.base import (
    AddSlashHandler,
    BaseHandler,
    cached,
    RemoveSlashHandler,
    RenderingHandler,
)

from nbviewer.utils import (
    base64_decode,
    quote,
    response_text,
)

from .client import AsyncGitLabClient


PROVIDER_CTX = {
    'provider_label': 'GitLab',
    'provider_icon': 'gitlab',
}


class GitLabClientMixin(object):
    @property
    def gitlab_client(self):
        """Create an upgraded gitlab API client from the HTTP client"""
        if getattr(self, "_gitlab_client", None) is None:
            self._gitlab_client = AsyncGitLabClient(self.client)
        return self._gitlab_client


class RawGitLabURLHandler(BaseHandler):
    """redirect old /urls/raw.gitlab urls to /gitlab/ API urls"""
    def get(self, user, repo, path):
        new_url = u'{format}/gitlab/{user}/{repo}/blob/{path}'.format(
            format=self.format_prefix, user=user, repo=repo, path=path,
        )
        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)


class GitLabRedirectHandler(GitLabClientMixin, BaseHandler):
    """redirect gitlab blob|tree|raw urls to /gitlab/ API urls"""
    def get(self, user, repo, app, ref, path):
        if app == 'raw':
            app = 'blob'
        new_url = u'{format}/gitlab/{user}/{repo}/{app}/{ref}/{path}'.format(
            format=self.format_prefix, user=user, repo=repo, app=app,
            ref=ref, path=path,
        )
        app_log.info("Redirecting %s to %s", self.request.uri, new_url)
        self.redirect(new_url)


class GitLabUserHandler(GitLabClientMixin, BaseHandler):
    """list a user's gitlab repos"""
    @cached
    @gen.coroutine
    def get(self, user):
        page = self.get_argument("page", None)
        params = {'sort' : 'updated'}
        if page:
            params['page'] = page
        with self.catch_client_error():
            response = yield self.gitlab_client.get_repos(user, params=params)

        prev_url, next_url = self.get_page_links(response)
        repos = json.loads(response_text(response))

        entries = []
        for repo in repos:
            entries.append(dict(
                url=repo['name'],
                name=repo['name'],
            ))
        provider_url = u"https://gitlab.com/{user}".format(user=user)
        html = self.render_template("userview.html",
            entries=entries, provider_url=provider_url,
            next_url=next_url, prev_url=prev_url,
            **PROVIDER_CTX
        )
        yield self.cache_and_finish(html)


class GitLabRepoHandler(BaseHandler):
    """redirect /gitlab/user/repo to .../tree/master"""
    def get(self, user, repo):
        self.redirect("%s/gitlab/%s/%s/tree/master/" % (self.format_prefix, user, repo))


class GitLabTreeHandler(GitLabClientMixin, BaseHandler):
    """list files in a gitlab repo (like gitlab tree)"""
    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
        if not self.request.uri.endswith('/'):
            self.redirect(self.request.uri + '/')
            return
        path = path.rstrip('/')
        with self.catch_client_error():
            response = yield self.gitlab_client.get_contents(user, repo, path, ref=ref)

        contents = json.loads(response_text(response))

        branches, tags = yield self.refs(user, repo)

        for nav_ref in branches + tags:
            nav_ref["url"] = (u"/gitlab/{user}/{repo}/tree/{ref}/{path}"
                .format(
                    ref=nav_ref["name"], user=user, repo=repo, path=path
                ))

        if not isinstance(contents, list):
            app_log.info(
                "{format}/{user}/{repo}/{ref}/{path} not tree, redirecting to blob",
                extra=dict(format=self.format_prefix, user=user, repo=repo, ref=ref, path=path)
            )
            self.redirect(
                u"{format}/gitlab/{user}/{repo}/blob/{ref}/{path}".format(
                    format=self.format_prefix, user=user, repo=repo, ref=ref, path=path,
                )
            )
            return

        base_url = u"/gitlab/{user}/{repo}/tree/{ref}".format(
            user=user, repo=repo, ref=ref,
        )
        provider_url = u"https://gitlab.com/{user}/{repo}/tree/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=path,
        )

        breadcrumbs = [{
            'url' : base_url,
            'name' : repo,
        }]
        breadcrumbs.extend(self.breadcrumbs(path, base_url))

        entries = []
        dirs = []
        ipynbs = []
        others = []
        for file in contents:
            e = {}
            e['name'] = file['name']
            if file['type'] == 'dir':
                e['url'] = u'/gitlab/{user}/{repo}/tree/{ref}/{path}'.format(
                user=user, repo=repo, ref=ref, path=file['path']
                )
                e['url'] = quote(e['url'])
                e['class'] = 'fa-folder-open'
                dirs.append(e)
            elif file['name'].endswith('.ipynb'):
                e['url'] = u'/gitlab/{user}/{repo}/blob/{ref}/{path}'.format(
                user=user, repo=repo, ref=ref, path=file['path']
                )
                e['url'] = quote(e['url'])
                e['class'] = 'fa-book'
                ipynbs.append(e)
            elif file['html_url']:
                e['url'] = file['html_url']
                e['class'] = 'fa-share'
                others.append(e)
            else:
                # submodules don't have html_url
                e['url'] = ''
                e['class'] = 'fa-folder-close'
                others.append(e)


        entries.extend(dirs)
        entries.extend(ipynbs)
        entries.extend(others)

        html = self.render_template("treelist.html",
            entries=entries, breadcrumbs=breadcrumbs, provider_url=provider_url,
            user=user, repo=repo, ref=ref, path=path,
            branches=branches, tags=tags, tree_type="gitlab",
            **PROVIDER_CTX
        )
        yield self.cache_and_finish(html)

    @gen.coroutine
    def refs(self, user, repo):
        """get branches and tags for this user/repo"""
        ref_types = ("branches", "tags")
        ref_data = [None, None]

        for i, ref_type in enumerate(ref_types):
            with self.catch_client_error():
                response = yield getattr(self.gitlab_client, "get_%s" % ref_type)(user, repo)
            ref_data[i] = json.loads(response_text(response))

        raise gen.Return(ref_data)


class GitLabBlobHandler(GitLabClientMixin, RenderingHandler):
    """handler for files on gitlab

    If it's a...

    - notebook, render it
    - non-notebook file, serve file unmodified
    - directory, redirect to tree
    """
    @cached
    @gen.coroutine
    def get(self, user, repo, ref, path):
        raw_url = u"https://raw.gitlabusercontent.com/{user}/{repo}/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path)
        )
        blob_url = u"https://gitlab.com/{user}/{repo}/blob/{ref}/{path}".format(
            user=user, repo=repo, ref=ref, path=quote(path),
        )
        with self.catch_client_error():
            tree_entry = yield self.gitlab_client.get_tree_entry(
                user, repo, path=path, ref=ref
            )

        if tree_entry['type'] == 'tree':
            tree_url = "/gitlab/{user}/{repo}/tree/{ref}/{path}/".format(
                user=user, repo=repo, ref=ref, path=quote(path),
            )
            app_log.info("%s is a directory, redirecting to %s", self.request.path, tree_url)
            self.redirect(tree_url)
            return

        # fetch file data from the blobs API
        with self.catch_client_error():
            response = yield self.gitlab_client.fetch(tree_entry['url'])

        data = json.loads(response_text(response))
        contents = data['content']
        if data['encoding'] == 'base64':
            # filedata will be bytes
            filedata = base64_decode(contents)
        else:
            # filedata will be unicode
            filedata = contents

        if path.endswith('.ipynb'):
            dir_path = path.rsplit('/', 1)[0]
            base_url = "/gitlab/{user}/{repo}/tree/{ref}".format(
                user=user, repo=repo, ref=ref,
            )
            breadcrumbs = [{
                'url' : base_url,
                'name' : repo,
            }]
            breadcrumbs.extend(self.breadcrumbs(dir_path, base_url))

            try:
                # filedata may be bytes, but we need text
                if isinstance(filedata, bytes):
                    nbjson = filedata.decode('utf-8')
                else:
                    nbjson = filedata
            except Exception as e:
                app_log.error("Failed to decode notebook: %s", raw_url, exc_info=True)
                raise web.HTTPError(400)
            yield self.finish_notebook(nbjson, raw_url,
                provider_url=blob_url,
                breadcrumbs=breadcrumbs,
                msg="file from GitLab: %s" % raw_url,
                public=True,
                format=self.format,
                request=self.request,
                **PROVIDER_CTX
            )
        else:
            mime, enc = mimetypes.guess_type(path)
            self.set_header("Content-Type", mime or 'text/plain')
            self.cache_and_finish(filedata)


def default_handlers(handlers=[]):
    """Tornado handlers"""

    return [
        (r'/gitlab/([^\/]+)', AddSlashHandler),
        (r'/gitlab/([^\/]+)/', GitLabUserHandler),
        (r'/gitlab/([^\/]+)/([^\/]+)', AddSlashHandler),
        (r'/gitlab/([^\/]+)/([^\/]+)/', GitLabRepoHandler),
        (r'/gitlab/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)/', RemoveSlashHandler),
        (r'/gitlab/([^\/]+)/([^\/]+)/blob/([^\/]+)/(.*)', GitLabBlobHandler),
        (r'/gitlab/([^\/]+)/([^\/]+)/tree/([^\/]+)', AddSlashHandler),
        (r'/gitlab/([^\/]+)/([^\/]+)/tree/([^\/]+)/(.*)', GitLabTreeHandler)
    ]

default_handlers.weight = 250


def uri_rewrites(rewrites=[]):
    return rewrites + [
        (r'^https?://gitlab.com/([\w\-]+)/([^\/]+)/(blob|tree)/(.*)$',
            u'/gitlab/{0}/{1}/{2}/{3}'),
        (r'^https?://raw.?gitlab.com/([\w\-]+)/([^\/]+)/(.*)$',
            u'/gitlab/{0}/{1}/blob/{2}'),
        (r'^([\w\-]+)/([^\/]+)$',
            u'/gitlab/{0}/{1}/tree/master/'),
        (r'^([\w\-]+)$',
            u'/gitlab/{0}/'),
    ]

uri_rewrites.weight = 250
