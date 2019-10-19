from pony import orm


db = orm.Database()


class User(db.Entity):
    id = orm.PrimaryKey(int, auto=True)
    email = orm.Required(str, unique=True)
    password = orm.Required(str)
    cameras = orm.Set('Camera')


class Camera(db.Entity):
    id = orm.PrimaryKey(int, auto=True)
    connection_string = orm.Required(str, unique=True)
    description = orm.Required(str)
    users = orm.Set(User)
