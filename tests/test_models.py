from pony.orm import db_session, set_sql_debug, commit, rollback
from pony.orm.core import CacheIndexError

from pytest import fixture

from smart_spy_api.models import db, User, Camera


# Debug mode
set_sql_debug(True)


@fixture
def db_url(tmp_path):
    return str(tmp_path / 'test_models.sqlite')


@fixture
def database(db_url):
    db.bind('sqlite', db_url, create_db=True)
    db.generate_mapping(create_tables=True)


# Test database creation
@db_session
def test_user_creation(database):
    user = User(email='carlos', password='1234')
    commit()
    assert user.id is not None and user.email == 'carlos'


@db_session
def test_user_creation_already_exists():
    User(email='abc', password='1234')
    try:
        User(email='abc', password='1234')
    except CacheIndexError as ex:
        assert str(ex) == "Cannot create User: value 'abc' for key email already exists"
    rollback()


@db_session
def test_camera_creation():
    camera = Camera(connection_string='abc123', description='xyz')
    commit()
    assert camera.id is not None and camera.connection_string == 'abc123'


@db_session
def test_add_camera_to_user():
    user1 = User[1]
    user2 = User(email='abc', password='1234')
    camera = Camera[1]
    user1.cameras.add(camera)
    user2.cameras.add(camera)

    users = camera.users.select()[:]
    assert users[0].email == user1.email and users[1].email == user2.email
