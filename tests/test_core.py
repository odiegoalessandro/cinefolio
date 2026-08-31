import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from server.database.connection import get_connection, initialize_database
from server.repositories.movie_repository import MovieRepository
from server.repositories.user_movie_repository import UserMovieRepository
from server.repositories.user_repository import UserRepository
from server.services.auth_service import AuthService, hash_password, verify_password
from server.services.profile_service import ProfileService

class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False); self.temp.close()
        initialize_database(self.temp.name); self.connection = get_connection(self.temp.name)
        self.users = UserRepository(self.connection); self.movies = MovieRepository(self.connection); self.user_movies = UserMovieRepository(self.connection)
    def tearDown(self): self.connection.close(); os.unlink(self.temp.name)
    def user(self, name='diego'): return self.users.create(name, 'Diego', hash_password('senhasegura'))
    def movie(self, tmdb_id=550): return self.movies.upsert({'tmdb_id':tmdb_id,'title':'Fight Club','release_year':1999})
    def test_schema_enforces_unique_and_foreign_keys(self):
        self.user()
        with self.assertRaises(Exception): self.user()
        with self.assertRaises(Exception): self.connection.execute("INSERT INTO user_movies VALUES (999, 999, 'WATCHED', NULL, NULL, 0, NULL, 'x', 'x')")
    def test_movie_crud_and_statistics(self):
        user, movie = self.user(), self.movie()
        self.user_movies.upsert(user['id'], movie['id'], 'WATCHED', rating=8.5, review='Ótimo', favorite=True, watched_at='2026-01-01')
        row=self.user_movies.list_for_profile(user['id'], favorite=True)[0]; self.assertEqual(row['title'], 'Fight Club'); self.assertEqual(row['rating'], 8.5)
        stats=self.user_movies.statistics(user['id']); self.assertEqual(stats['watched_count'], 1); self.assertEqual(stats['average_rating'], 8.5)
        self.assertTrue(self.user_movies.remove(user['id'],movie['id'])); self.assertFalse(self.user_movies.remove(user['id'],movie['id']))
    def test_invalid_status_rejected(self):
        user,movie=self.user(),self.movie()
        with self.assertRaises(Exception): self.user_movies.upsert(user['id'],movie['id'],'INVALID')
    def test_profile_groups_movies(self):
        user=self.user(); watched=self.movie(1); watching=self.movie(2)
        self.user_movies.upsert(user['id'], watched['id'], 'WATCHED', favorite=True, watched_at='2026-01-01')
        self.user_movies.upsert(user['id'], watching['id'], 'WATCHING')
        profile=ProfileService(self.users,self.user_movies).public_profile('diego')
        self.assertEqual(len(profile['sections']['favorites']),1); self.assertEqual(len(profile['sections']['watching']),1); self.assertNotIn('password_hash',profile)

class AuthTestCase(DatabaseTestCase):
    def test_hash_uses_salt_and_verifies(self):
        first,second=hash_password('senhasegura'),hash_password('senhasegura')
        self.assertNotEqual(first,second); self.assertTrue(verify_password('senhasegura',first)); self.assertFalse(verify_password('errada',first))
    def test_register_login_and_session(self):
        auth=AuthService(self.users); user=auth.register('cinema_user','Cinema User','senhasegura')
        logged,token=auth.login('cinema_user','senhasegura'); self.assertEqual(user['id'],logged['id']); self.assertEqual(auth.current_user(token)['id'],user['id'])
        auth.logout(token); self.assertIsNone(auth.current_user(token))
    def test_auth_rejects_invalid_input(self):
        auth=AuthService(self.users)
        with self.assertRaises(ValueError): auth.register('x','Nome','123')
        with self.assertRaises(ValueError): auth.login('missing','senha')

if __name__ == '__main__': unittest.main()
