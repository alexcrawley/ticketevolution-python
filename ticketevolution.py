'''A library that provides a Python interface to the TicketEvolution API'''

__author__ = 'derekdahmer@gmail.com'
__version__ = '0.0.1'


import urllib
import urllib2

import urlparse
import gzip
import StringIO
import hmac, hashlib, base64


class Api(object):  
    def __init__(self,
                 client_token=None,
                 client_secret=None):

        self.client_token = client_token
        self.client_secret = client_secret

        self._default_params = {}
        self._urllib         = urllib2
        self._input_encoding = None

    def _FetchUrl(self,
                  url,
                  http_method = 'GET',
                  post_data=None,
                  parameters=None):
        '''Fetch a URL, optionally caching for a specified time.

        Args:
          url:
            The full URL to retrieve
          post_data:
            A dict of (str, unicode) key/value pairs.
            If set, POST will be used.
          parameters:
            A dict whose key/value pairs should encoded and added
            to the query string. [Optional]

        Returns:
          A string containing the body of the response.
        '''
        # Build the extra parameters dict
        extra_params = {}
        if self._default_params:
            extra_params.update(self._default_params)
        if parameters:
            extra_params.update(parameters)

        http_handler  = self._urllib.HTTPHandler()
        https_handler = self._urllib.HTTPSHandler()

        opener = self._urllib.OpenerDirector()
        opener.add_handler(http_handler)
        opener.add_handler(https_handler)


        url = self._BuildUrl(url, extra_params=extra_params)

        # TODO: This will need to be changed to a JSON converter, or just 
        # removed and take a JSON string
        encoded_post_data = self._EncodePostData(post_data)

        print "URL: %s" % url
        print "Post Data: %s" % encoded_post_data

        # Sign request here
        signature = self._generate_signature(http_method, url, encoded_post_data)
        headers = {
            'Accept':"application/vnd.ticketevolution.api+json; version=8",
            'X-Signature':signature,
            'X-Token':self.client_token,
        }
        print headers

        # Open and return the URL immediately if we're not going to cache
        request = self._urllib.Request(url,encoded_post_data,headers)
        response = opener.open(request)
        url_data = self._DecompressGzippedResponse(response)
        opener.close()

        # Always return the latest version
        return url_data


    def _generate_signature(self,
                            http_method,
                            url = None, 
                            encoded_post_data = None):
        '''Creates a signature for the request using 
        either the URL for GET requests or the post data for other
        requests.
        '''

        if http_method == 'GET':
            # Remove the 'https://' from the url
            url_without_scheme = url.split("//",1)[1]

            request = "GET %s" % (url_without_scheme)
        else:
            request = encoded_post_data

        signature = hmac.new(
            digestmod=hashlib.sha256,
            key=self.client_secret,
            msg=request,
        ).digest()

        encoded_signature = base64.b64encode(signature)
        return encoded_signature


    def _Parse(self, json):
        '''Parse the returned json string
        '''
        try:
            data = simplejson.loads(json)
        except ValueError:
            return data

    def _Encode(self, s):
        if self._input_encoding:
            return unicode(s, self._input_encoding).encode('utf-8')
        else:
            return unicode(s).encode('utf-8')

    def _EncodeParameters(self, parameters):
        '''Return a string in key=value&key=value form

        Values of None are not included in the output string.

        Args:
            parameters:
                A dict of (key, value) tuples, where value is encoded as
                specified by self._encoding

        Returns:
            A URL-encoded string in "key=value&key=value" form
        '''
        if parameters is None:
          return None
        else:
          return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in parameters.items() if v is not None]))

    def _EncodePostData(self, post_data):
        '''Return a string in key=value&key=value form

        Values are assumed to be encoded in the format specified by self._encoding,
        and are subsequently URL encoded.

        Args:
          post_data:
            A dict of (key, value) tuples, where value is encoded as
            specified by self._encoding

        Returns:
          A URL-encoded string in "key=value&key=value" form
        '''
        if post_data is None:
            return None
        else:
            return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in post_data.items()]))


    def _DecompressGzippedResponse(self, response):
        raw_data = response.read()
        if response.headers.get('content-encoding', None) == 'gzip':
            url_data = gzip.GzipFile(fileobj=StringIO.StringIO(raw_data)).read()
        else:
            url_data = raw_data
        return url_data

    def _BuildUrl(self, url, path_elements=None, extra_params=None):
        # Break url into consituent parts
        (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

        # Add any additional path elements to the path
        if path_elements:
            # Filter out the path elements that have a value of None
            p = [i for i in path_elements if i]
            if not path.endswith('/'):
                path += '/'
                path += '/'.join(p)

        # Add any additional query parameters to the query string
        if extra_params and len(extra_params) > 0:
            extra_query = self._EncodeParameters(extra_params)
            # Add it to the existing query
            if query:
                query += '&' + extra_query
            else:
                query = extra_query

        # Return the rebuilt URL
        return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))