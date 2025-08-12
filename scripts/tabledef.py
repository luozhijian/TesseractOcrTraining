# -*- coding: utf-8 -*-

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Local
SQLALCHEMY_DATABASE_URI = 'sqlite:////var/www/tesseracttraining/accounts.db'

# Heroku
#SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

Base = declarative_base()


def db_connect():
    """
    Performs database connection using database settings from settings.py.
    Returns sqlalchemy engine instance
    """
    return create_engine(SQLALCHEMY_DATABASE_URI)


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String(30), unique=True)
    password = Column(String(512))
    email = Column(String(50))

    def __repr__(self):
        return '<User %r>' % self.username


class ForumPost(Base):
    __tablename__ = "forum_post"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    image_filename = Column(String(255), nullable=True)
    importance = Column(Integer, nullable=False, default=0)
    
    author = relationship("User")
    replies = relationship("ForumReply", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return '<ForumPost %r>' % self.title


class ForumReply(Base):
    __tablename__ = "forum_reply"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('forum_post.id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    image_filename = Column(String(255), nullable=True)
    
    author = relationship("User")
    post = relationship("ForumPost", back_populates="replies")

    def __repr__(self):
        return '<ForumReply %r>' % self.id


engine = db_connect()  # Connect to database
Base.metadata.create_all(engine)  # Create models
