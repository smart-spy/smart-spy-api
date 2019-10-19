from pytest import fixture

from smart_spy_api.controllers import configure_database, UserController, CameraController
from smart_spy_api import schemas


@fixture
def db_url(tmp_path):
    return str(tmp_path / 'test_controllers.sqlite')


def test_configuration(db_url):
    configure_database(provider='sqlite', filename=db_url, create_db=True)
    assert 1 == 1


# User CRUD
def test_create_user():
    user = schemas.UserCreate(**{'email': 'carlos porta', 'password': 'abc123'})
    user = UserController.create(user)
    assert user.email == 'carlos porta'


def test_create_user_already_exists():
    user = schemas.UserCreate(**{'email': 'carlos porta', 'password': 'abc123'})
    try:
        UserController.create(user)
        assert 2 == 1
    except Exception:
        assert 1 == 1


def test_read_user():
    user = UserController.read(1)
    user.email == 'carlos porta'


def test_update_user():
    user_create = schemas.UserCreate(**{'email': 'porta', 'password': 'abc123'})
    user_update = schemas.UserUpdate(email='asd', password='asodkasod')

    user_created = UserController.create(user_create)

    updated_user = UserController.update(user_created.id, user_update)
    assert updated_user.email == 'asd'


def test_delete_user():
    UserController.delete(1)
    assert 1 == 1


# Camera CRUD
def test_create_camera():
    camera = schemas.CameraCreate(**{'connection_string': 'abc123', 'description': 'descr'})
    camera = CameraController.create(camera)
    camera.connection_string == 'abc123'


def test_create_camera_already_exists():
    camera = schemas.CameraCreate(**{'connection_string': 'abc123', 'description': 'descr'})
    try:
        CameraController.create(camera)
        assert 1 == 0
    except Exception:
        assert 1 == 1


def test_read_camera():
    camera = CameraController.read(1)
    camera.connection_string == 'abc123' and camera.description == 'descr'


def test_update_camera():
    camera_create = schemas.CameraCreate(**{'connection_string': 'abc', 'description': 'descr'})
    camera_update = schemas.CameraUpdate(connection_string='xyz')

    camera_created = CameraController.create(camera_create)

    updated_camera = CameraController.update(camera_created.id, camera_update)
    assert updated_camera.connection_string == camera_update.connection_string

    camera_update = schemas.CameraUpdate(description='ioioio')
    updated_camera = CameraController.update(camera_created.id, camera_update)

    assert updated_camera.description == camera_update.description


def test_delete_camera():
    CameraController.delete(1)
    assert 1 == 1


# # Camera and User
# def test_add_camera_to_user():
#     user = schemas.UserCreate(**{'email': 'carlos porta', 'password': 'abc123'})
#     user = UserController.create(user)

#     camera = schemas.CameraCreate(**{'connection_string': 'sadadddf'})
#     camera1 = CameraController.create(camera)

#     camera = schemas.CameraCreate(**{'connection_string': 'sdsosk'})
#     camera2 = CameraController.create(camera)

#     UserController.add_cameras(user.id, [camera1.id, camera2.id])

#     user = UserController.read(user.id)
#     len(user.cameras) == 2
