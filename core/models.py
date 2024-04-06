import datetime
from core import db, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


class Users(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Store hashed passwords
    isAdmin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(), nullable=False)
    last_login = db.Column(db.DateTime, default=datetime.datetime.now(), nullable=False)
    files = db.relationship('File', backref='creator', lazy=True)


class Group(db.Model):
    __tablename__ = "group"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(255))


class Project(db.Model):
    __tablename__ = "project"

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(255), nullable=False)


class File(db.Model):
    __tablename__ = "file"

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    project_id = db.Column(db.String, db.ForeignKey("project.id"), nullable=False)
    visibility_flag = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class User_Group(db.Model):
    __tablename__ = "user_group"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), primary_key=True)


class File_Permissions_User(db.Model):
    __tablename__ = "file_permissions_user"

    permission_id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String, db.ForeignKey("file.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    permission_type = db.Column(db.String(50), nullable=False)


class File_Permissions_Group(db.Model):
    __tablename__ = "file_permissions_group"

    permission_id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String, db.ForeignKey("file.id"), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    permission_type = db.Column(db.String(50), nullable=False)
