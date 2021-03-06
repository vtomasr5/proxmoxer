__author__ = 'Oleg Butovich'
__copyright__ = '(c) Oleg Butovich 2013'
__licence__ = 'MIT'

import httplib
import os
import imp
import urlparse
import posixpath
import logging

logger = logging.getLogger(__name__)


class ProxmoxResourceBase(object):

    def __getattr__(self, item):
        if item.startswith("_"):
            raise AttributeError(item)

        kwargs = self._store.copy()
        kwargs['base_url'] = self.url_join(self._store["base_url"], item)

        return ProxmoxResource(**kwargs)

    def url_join(self, base, *args):
        scheme, netloc, path, query, fragment = urlparse.urlsplit(base)
        path = path if len(path) else "/"
        path = posixpath.join(path, *[('%s' % x) for x in args])
        return urlparse.urlunsplit([scheme, netloc, path, query, fragment])


class ResourceException(StandardError):
    pass


class ProxmoxResource(ProxmoxResourceBase):

    def __init__(self, **kwargs):
        self._store = kwargs

    def __call__(self, resource_id=None):
        if not resource_id:
            return self

        if isinstance(resource_id, basestring):
            resource_id = resource_id.split("/")
        elif not isinstance(resource_id, (tuple, list)):
            resource_id = [str(resource_id)]

        kwargs = self._store.copy()
        if resource_id is not None:
            kwargs["base_url"] = self.url_join(self._store["base_url"], *resource_id)

        return self.__class__(**kwargs)

    def _request(self, method, data=None, params=None):
        url = self._store["base_url"]
        if data:
            logger.info('%s %s %r', method, url, data)
        else:
            logger.info('%s %s', method, url)
        resp = self._store["session"].request(method, url, data=data or None, params=params)
        logger.debug('Status code: %s, output: %s', resp.status_code, resp.content)

        if resp.status_code >= 400:
            raise ResourceException("{0} {1}".format(resp.status_code, httplib.responses[resp.status_code]))
        elif 200 <= resp.status_code <= 299:
            return self._store["serializer"].loads(resp)

    def get(self, *args, **params):
        return self(args)._request("GET", params=params)

    def post(self, *args, **data):
        return self(args)._request("POST", data=data)

    def put(self, *args, **data):
        return self(args)._request("PUT", data=data)

    def delete(self, *args, **params):
        return self(args)._request("DELETE", params=params)

    def create(self, *args, **data):
        return self.post(*args, **data)

    def set(self, *args, **data):
        return self.put(*args, **data)


class ProxmoxAPI(ProxmoxResourceBase):
    def __init__(self, host, backend='https', **kwargs):

        #load backend module
        found_module = imp.find_module(backend, [os.path.join(os.path.dirname(__file__), 'backends')])
        self._backend = imp.load_module(backend, *found_module).Backend(host, **kwargs)

        self._store = {
            "base_url": self._backend.get_base_url(),
            "session": self._backend.get_session(),
            "serializer": self._backend.get_serializer(),
        }