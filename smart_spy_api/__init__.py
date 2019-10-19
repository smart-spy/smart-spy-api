from asyncio import create_task, sleep
from typing import List
from json import dumps

from datetime import datetime
from datetime import timedelta
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import encode, decode, PyJWTError
from pony.orm.core import TransactionIntegrityError, ObjectNotFound
from pony.orm.dbapiprovider import IntegrityError
from starlette import status as http_status
from starlette.config import Config
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response, HTMLResponse
from starlette.websockets import WebSocket


from smart_spy_api.controllers import configure_database, UserController, CameraController
from smart_spy_api import schemas
from smart_spy_api.stream import StreamService, html


config = Config('.env')
SECRET_KEY = config('SECRET_KEY', cast=str)
DATABASE = config('DATABASE', cast=str)

app = FastAPI(
    title="PUC-MG 2019",
    description="Smart-Spy API",
    version="1.0.0",)


app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    configure_database(provider='sqlite', filename=DATABASE, create_db=True)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


async def get_identity(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=http_status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode(token, SECRET_KEY)
        user_id: int = payload.get("identity")
        if user_id is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    try:
        user = UserController.read(user_id)
    except ObjectNotFound:
        raise credentials_exception
    return user.id


@app.post("/login", tags=['Auth'])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        email = form_data.username
        password = form_data.password
        if not(email or password):
            HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail='unauthorized')

        if UserController.authenticate(email, password):
            user = UserController.read_by_email(email)
            user_id = user.id
            payload = dict(identity=user_id, exp=datetime.utcnow() + timedelta(hours=24))
            token = encode(payload, SECRET_KEY)
            return {"access_token": token, "token_type": "bearer", "user_id": user_id}
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail='unauthorized')            
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='user not found')


@app.post('/users',
          response_model=schemas.User,
          status_code=http_status.HTTP_201_CREATED,
          tags=['User'])
async def create_user(user: schemas.UserCreate, response: Response) -> schemas.User:
    try:
        user = UserController.create(user)
        return user
    except TransactionIntegrityError:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail='email already exists')


@app.get('/users', response_model=List[schemas.User], tags=['User'])
async def read_all_users():
    users = UserController.read_all()
    return users


@app.get('/users/{user_id}', response_model=schemas.User, tags=['User'])
async def read_user(user_id: int):
    try:
        user = UserController.read(user_id)
        return user
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='user not found')


@app.put('/users/{user_id}', tags=['User'])
async def update_user(user_id: int, user: schemas.UserUpdate, logged_user_id: int = Depends(get_identity)):
    if user_id != logged_user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail='FORBIDDEN')
    try:
        user = UserController.update(user_id, user)
        return user
    except IntegrityError:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail='email already exists')


@app.delete('/users/{user_id}', tags=['User'])
async def delete_user(user_id: int, logged_user_id: int = Depends(get_identity)):
    if user_id != logged_user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail='FORBIDDEN')
    try:
        UserController.delete(user_id)
        return {'msg': 'ok'}
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='user not found')


@app.get('/users/{user_id}/cameras/', tags=['UserCamera'])
async def read_user_cameras(user_id: int, logged_user_id: int = Depends(get_identity)):
    if user_id != logged_user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail='FORBIDDEN')
    try:
        cameras = UserController.read_user_cameras(user_id)
        return cameras
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='user not found')


@app.post('/users/{user_id}/cameras/',
          response_model=schemas.Camera,
          status_code=http_status.HTTP_201_CREATED,
          tags=['UserCamera'])
async def create_user_camera(user_id: int, camera: schemas.CameraCreate, logged_user_id: int = Depends(get_identity)):
    if user_id != logged_user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail='FORBIDDEN')
    try:
        created_camera = CameraController.create(camera)
        return UserController.add_cameras(user_id, created_camera.id)
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='user not found')
    except TransactionIntegrityError:
        camera_in_db = CameraController.read_by_connection_string(camera.connection_string)
        return UserController.add_cameras(user_id, camera_in_db.id)
        # raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail='camera already exists')


@app.get('/users/{user_id}/cameras/{camera_id}', tags=['UserCamera'])
async def read_user_camera(user_id: int, camera_id: int, logged_user_id: int = Depends(get_identity)):
    if user_id != logged_user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail='FORBIDDEN')
    try:
        _ = UserController.read(user_id)
        return CameraController.read(camera_id)
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='user/camera not found')


@app.put('/users/{user_id}/cameras/{camera_id}', tags=['UserCamera'])
async def update_camera(user_id: int, camera_id: int, camera: schemas.CameraUpdate, logged_user_id: int = Depends(get_identity)):
    if user_id != logged_user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail='FORBIDDEN')
    try:
        _ = UserController.read(user_id)
        updated_camera = CameraController.update(camera_id, camera)
        return updated_camera
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='user/camera not found')
    except IntegrityError:
        raise HTTPException(status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail='camera already exists')


@app.delete('/users/{user_id}/cameras/{camera_id}', tags=['UserCamera'])
async def delete_user_camera(user_id: int, camera_id: int, logged_user_id: int = Depends(get_identity)):
    if user_id != logged_user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail='FORBIDDEN')
    try:
        _ = UserController.read(user_id)
        CameraController.delete(camera_id)
        return {'msg': 'ok'}
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='user/camera not found')


@app.get('/cameras/', tags=['Camera'])
async def read_cameras():
    try:
        cameras = CameraController.read_all()
        return cameras
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='user not found')


@app.delete('/cameras/{camera_id}', tags=['Camera'])
async def delete_camera(camera_id: int, user_id: int = Depends(get_identity)):
    try:
        CameraController.delete(camera_id)
        return {'msg': 'ok'}
    except ObjectNotFound:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail='camera not found')


@app.get("/users/{user_id}/cameras/{camera_id}/stream/", tags=["StreamTest"])
async def stream_test(user_id: int, camera_id: int):
    UserController.read(user_id)
    CameraController.read(camera_id)
    _html = html.replace("{user_id}", str(user_id)).replace("{camera_id}", str(camera_id))
    return HTMLResponse(_html)


@app.get("/users/{user_id}/cameras/{camera_id}/stream/smart-spy", tags=["StreamTest"])
async def smart_spy_test(user_id: int, camera_id: int):
    UserController.read(user_id)
    CameraController.read(camera_id)
    _html = html.replace("{user_id}", str(user_id)).replace("{camera_id}", str(camera_id))
    return HTMLResponse(_html)


@app.websocket("/users/{user_id}/cameras/{camera_id}/stream/smart-spy/ws")
async def smart_spy_endpoint(user_id: int, camera_id: int, websocket: WebSocket):
    _ = UserController.read(user_id)
    camera = CameraController.read(camera_id)
    uri = camera.connection_string

    if uri.startswith('int:'):
        uri = int(uri.replace('int:', ''))

    await websocket.accept()
    await StreamService.add(uri)
    create_task(StreamService.run_x_seconds(uri, detect=True))

    await sleep(1)
    while await StreamService.is_active(uri):
        print(0)
        resp = await StreamService.read(uri)
        if resp:
            await sleep(0.1)
            print(1)
            await websocket.send_text(dumps(resp))
            print(2)


@app.websocket("/users/{user_id}/cameras/{camera_id}/stream/ws")
async def stream_endpoint(user_id: int, camera_id: int, websocket: WebSocket):
    _ = UserController.read(user_id)
    camera = CameraController.read(camera_id)
    uri = camera.connection_string

    if uri.startswith('int:'):
        uri = int(uri.replace('int:', ''))

    await websocket.accept()
    await StreamService.add(uri)
    create_task(StreamService.run_x_seconds(uri))

    await sleep(1)
    while await StreamService.is_active(uri):
        resp = await StreamService.read(uri)
        if resp:
            await websocket.send_json(str(resp))
