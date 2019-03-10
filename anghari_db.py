import contextlib
from sqlalchemy import create_engine
from sqlalchemy import Column, ForeignKey, TEXT, INTEGER, DATE, FLOAT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

base = declarative_base()


class Watchables(base):
    __tablename__ = 'watchables'

    id = Column(INTEGER, primary_key=True)
    title = Column(TEXT, nullable=False)
    year = Column(INTEGER, nullable=False)
    episodes = Column(INTEGER, nullable=False)
    baselink = Column(TEXT, nullable=False)
    remarks = Column(TEXT)
    datetimeadded = Column(DATE, nullable=False)
    lastupdate = Column(DATE, nullable=False)

    def __str__(self):
        return f'[{self.year}] - {self.title}'


class Status(base):
    __tablename__ = 'status'

    sid = Column(INTEGER, primary_key=True)
    id = Column(INTEGER, ForeignKey(Watchables.id), nullable=False)
    status = Column(TEXT, nullable=False)
    progress = Column(FLOAT, nullable=False)
    location = Column(TEXT, nullable=False)
    lastupdate = Column(DATE, nullable=False)
    remarks = Column(TEXT)


class Episodes(base):
    __tablename__ = 'episodes'

    episodes_id = Column(INTEGER, primary_key=True)
    id = Column(INTEGER, ForeignKey(Watchables.id), nullable=False)
    episode = Column(INTEGER, nullable=False)
    status = Column(TEXT, nullable=False)
    base_link = Column(TEXT, nullable=False)
    download_link = Column(TEXT, nullable=False)
    progress = Column(FLOAT, nullable=False)
    size= Column(INTEGER, nullable=False)
    duration = Column(INTEGER)
    remarks = Column(TEXT)
    datetimeadded = Column(DATE, nullable=False)
    lastupdate = Column(DATE, nullable=False)
    location = Column(TEXT)


@contextlib.contextmanager
def get_session():
    db_string = "postgres://chester:hello987@localhost:5432/anghari_db"
    db = create_engine(db_string, poolclass=NullPool)
    asd = sessionmaker(db)
    __session: Session = asd()
    try:
        yield __session
    finally:
        __session.close()

