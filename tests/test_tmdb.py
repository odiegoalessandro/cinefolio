import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import URLError

from server.services.tmdb_service import TmdbService

class Response:
    def __init__(self, data): self.data=data
    def __enter__(self): return self
    def __exit__(self,*args): return None
    def read(self): return json.dumps(self.data).encode()

class TmdbServiceTests(unittest.TestCase):
    def test_search_normalizes_catalog_result(self):
        opener=Mock(return_value=Response({'results':[{'id':550,'title':'Fight Club','original_title':'Fight Club','release_date':'1999-10-15','poster_path':'/a.jpg'}]}))
        results=TmdbService('secret',opener).search('Fight Club')
        self.assertEqual(results[0]['tmdb_id'],550); self.assertEqual(results[0]['release_year'],1999)
        request=opener.call_args[0][0]; self.assertIn('Bearer secret',request.headers['Authorization'])
    def test_rejects_empty_search_and_invalid_id(self):
        service=TmdbService('secret',Mock())
        with self.assertRaises(ValueError): service.search(' ')
        with self.assertRaises(ValueError): service.details('not-id')
    def test_hides_external_error_details(self):
        service=TmdbService('token-should-not-leak',Mock(side_effect=URLError('network')))
        with self.assertRaisesRegex(ValueError,'Não foi possível'): service.popular()
    def test_requires_server_token(self):
        with self.assertRaisesRegex(ValueError,'não está configurada'): TmdbService('',Mock()).popular()

if __name__ == '__main__': unittest.main()
