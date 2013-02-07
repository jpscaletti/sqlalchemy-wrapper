# -*- coding: utf-8 -*-
import re
import threading

from inflector import Inflector, English
import sqlalchemy
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.query import Query


inflector = Inflector(English)


def create_scoped_session(db):
    return scoped_session(sessionmaker(autocommit=False, autoflush=True,
        bind=db.engine, query_cls=Query))


def make_table(db):
    def table_maker(*args, **kwargs):
        if len(args) > 1 and isinstance(args[1], db.Column):
            args = (args[0], db.metadata) + args[2:]
        return sqlalchemy.Table(*args, **kwargs)
    return table_maker


def include_sqlalchemy(obj):
    for module in sqlalchemy, sqlalchemy.orm:
        for key in module.__all__:
            if not hasattr(obj, key):
                setattr(obj, key, getattr(module, key))
    obj.Table = make_table(obj)


CAMELCASE_RE = re.compile(r'([A-Z]+)(?=[a-z0-9])')


def get_table_name(classname):
    def _join(match):
        word = match.group()
        if len(word) > 1:
            return ('_%s_%s' % (word[:-1], word[-1])).lower()
        return '_' + word.lower()

    tname = CAMELCASE_RE.sub(_join, classname).lstrip('_')
    return inflector.pluralize(tname).lower()


class ModelTableNameDescriptor(object):

    def __get__(self, obj, type):
        tablename = type.__dict__.get('__tablename__')
        if not tablename:
            tablename = get_table_name(type.__name__)
            setattr(type, '__tablename__', tablename)
        return tablename


class EngineConnector(object):

    def __init__(self, sqlalch):
        self._sqlalch = sqlalch
        self._engine = None
        self._connected_for = None
        self._lock = threading.Lock()

    def get_engine(self):
        with self._lock:
            uri = self._sqlalch.uri
            info = self._sqlalch.info
            options = self._sqlalch.options
            echo = options.get('echo')
            if (uri, echo) == self._connected_for:
                return self._engine
            self._engine = engine = sqlalchemy.create_engine(info, **options)
            self._connected_for = (uri, echo)
            return engine


class Model(object):
    """Baseclass for custom user models."""

    __tablename__ = ModelTableNameDescriptor()
    
    def __iter__(self):
        """Returns an iterable that supports .next()
        so we can do dict(sa_instance).
        """
        for k in self.__dict__.keys():
            if not k.startswith('_'):
                yield (k, getattr(self, k))
    
    def __repr__(self):
        return '<%s>' % self.__class__.__name__

