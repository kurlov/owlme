#!flask/bin/python
import os
import unittest

from config import basedir
from app import app, db
from app.models import User

class TestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'test.db')
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_avatar(self):
        u = User(social_id='google$112276867608691908248', nickname='Aleksandr Kurlov', email='sasha.kurlov@gmail.com')
        avatar = u.avatar(128)
        expected = 'http://www.gravatar.com/avatar/55ea02cf92bae3284e155f489518ffa4?d=mm&s=128'
        assert avatar[0:len(expected)] == expected

    def test_make_unique_nickname(self):
        u = User(social_id='google$112276867608691908248', nickname='Aleksandr Kurlov', email='sasha.kurlov@gmail.com')
        db.session.add(u)
        db.session.commit()
        nickname = User.make_unique_nickname('Aleksandr Kurlov')
        assert nickname != 'Aleksandr Kurlov'
        u = User(social_id='google$112276867608691908248', nickname='Aleksandr Kurlov', email='sasha.kurlov@gmail.com')
        db.session.add(u)
        db.session.commit()
        nickname2 = User.make_unique_nickname('Aleksandr Kurlov')
        assert nickname2 != 'Aleksandr Kurlov'
        assert nickname2 != nickname

if __name__ == '__main__':
    unittest.main()