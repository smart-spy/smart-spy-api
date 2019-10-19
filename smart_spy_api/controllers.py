from functools import wraps
from typing import List

from passlib.context import CryptContext
from pony.orm import db_session
from pony.orm.serialization import to_dict

from smart_spy_api import models
from smart_spy_api import schemas


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def try_except(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as ex:
            return False, ex
    return wrapper


# @try_except
def configure_database(provider, filename, create_db):
    models.db.bind(provider=provider, filename=filename, create_db=create_db)
    models.db.generate_mapping(create_tables=True)


class UserController:
    @staticmethod
    @db_session
    def create(user: schemas.UserCreate) -> schemas.User:
        user.password = UserController.get_password_hash(user.password)
        db_user = models.User(**dict(user)).to_dict()
        return schemas.User(**db_user)

    @staticmethod
    @db_session
    def read_all() -> List[schemas.User]:
        users = models.User.select()[:]
        data = [to_dict(u)['User'][u.id] for u in users]
        user_list = [schemas.User(**d) for d in data]
        return user_list

    @staticmethod
    @db_session
    def read(id: int) -> schemas.User:
        db_user = models.User[id]
        data = to_dict(db_user)['User'][id]
        return schemas.User(**data)

    @staticmethod
    @db_session
    def read_by_email(email: str) -> schemas.User:
        db_user = models.User.get(email=email)
        data = to_dict(db_user)['User'][db_user.id]
        return schemas.User(**data)

    @staticmethod
    @db_session
    def update(id: int, user: schemas.UserUpdate) -> schemas.User:
        db_user = models.User[id]
        db_user_dict = db_user.to_dict()
        db_user_dict.update(**user.dict(skip_defaults=True))
        db_user.set(**db_user_dict)
        return schemas.User(**db_user.to_dict())

    @staticmethod
    @db_session
    def delete(id: int):
        models.User[id].delete()

    @staticmethod
    @db_session
    def read_user_cameras(user_id: int):
        user = models.User[user_id]
        data = to_dict(user.cameras)
        if data:
            return [value for key, value in data['Camera'].items()]
        else:
            return {}

    @staticmethod
    @db_session
    def add_cameras(user_id: int, camera_id: int):
        user = models.User[user_id]
        camera = models.Camera[camera_id]
        user.cameras.add(camera)
        return CameraController.read(camera_id)

    @staticmethod
    @db_session
    def authenticate(email: str, plain_password: str) -> bool:
        db_user = models.User.get(email=email)
        return db_user and UserController.verify_password(plain_password, db_user.password)

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return pwd_context.hash(password)


class CameraController:
    @staticmethod
    @db_session
    def create(camera: schemas.CameraCreate) -> schemas.Camera:
        db_camera = models.Camera(**dict(camera)).to_dict()
        return schemas.Camera(**db_camera)

    @staticmethod
    @db_session
    def read_by_connection_string(connection_string: str):
        db_camera = models.Camera.get(connection_string=connection_string)
        data = to_dict(db_camera)['Camera'][db_camera.id]
        return schemas.Camera(**data)

    @staticmethod
    @db_session
    def read(id: int) -> schemas.Camera:
        db_camera = models.Camera[id]
        data = to_dict(db_camera)['Camera'][id]
        return schemas.Camera(**data)

    @staticmethod
    @db_session
    def read_all() -> List[schemas.Camera]:
        query_data = models.Camera.select()[:]
        cameras = [c.to_dict() for c in query_data]
        return cameras

    @staticmethod
    @db_session
    def update(id: int, camera: schemas.CameraUpdate) -> schemas.Camera:
        db_camera = models.Camera[id]
        db_camera_dict = db_camera.to_dict()
        db_camera_dict.update(**camera.dict(skip_defaults=True))
        db_camera.set(**db_camera_dict)
        return schemas.Camera(**db_camera.to_dict())

    @staticmethod
    @db_session
    def delete(id: int):
        models.Camera[id].delete()
