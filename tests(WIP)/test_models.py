# -*- coding: utf-8 -*-
"""Model unit tests."""
import datetime as dt

import pytest

from webproject.models import Stats, Url, User

from .factories import UserFactory

# from webproject import db



@pytest.mark.usefixtures('db')
class TestUser:
    """User tests."""

    def test_get_by_id(self, db):
        """Get user by ID."""
        user = User('foo', 'foo@bar.com', password='myprecious')
        db.session.add(user)
        db.session.commit()

        retrieved = User.query.get(1)
        assert retrieved == user

    # def test_password_is_nullable(self):
    #     """Test null password."""
    #     user = User(username='foo', email='foo@bar.com')
    #     user.save()
    #     assert user.password is None

    def test_factory(self, db):
        """Test user factory."""
        user = UserFactory(password='myprecious')
        db.session.add(user)
        db.session.commit()
        assert bool(user.username)
        assert bool(user.email)
        assert user.check_password('myprecious')

    def test_check_password(self):
        """Check password."""
        user = User(username='foo', email='foo@bar.com',
                    password='foobarbaz123')
        assert user.check_password('foobarbaz123') is True
        assert user.check_password('barfoobaz') is False
    #
    # def test_full_name(self):
    #     """User full name."""
    #     user = UserFactory(first_name='Foo', last_name='Bar', )
    #     assert user.full_name == 'Foo Bar'

    # def test_roles(self):
    #     """Add a role to a user."""
    #     role = Role(name='admin')
    #     role.save()
    #     user = UserFactory()
    #     user.roles.append(role)
    #     user.save()
    #     assert role in user.roles


@pytest.mark.usefixtures('db')
class TestUrl:
    """Url tests."""

    def test_pub_date_defaults_to_datetime(self, db):
        """Test creation date."""
        url = Url(url='https://test', date=dt.datetime.now(), user_id=1)
        db.session.add(url)
        db.session.commit()
        url = Url.query.filter_by(url='https://test').first()
        assert bool(url.pub_date)
        assert isinstance(url.pub_date, dt.datetime)
