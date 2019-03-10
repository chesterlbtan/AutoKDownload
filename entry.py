
from data.settings import LOG_FOLDER
import datetime
import logging
import os
from anghari_db import Watchables, Status, get_session

# Initialize logger
if not os.path.exists(LOG_FOLDER):
    os.mkdir(LOG_FOLDER)
LOG_FILE = os.path.join(LOG_FOLDER, f"generatorLog_{datetime.date.today().strftime('%Y%m%d')}.log")
logging.basicConfig(filename=LOG_FILE, format='[%(asctime)s.%(msecs)03d] %(message)s',
                    datefmt=logging.Formatter.default_time_format, level=logging.INFO)
logging.info(f'Logger initialized in {LOG_FILE}')


def log(message: str):
    print(message)
    logging.info(message)


def register(title: str, year: int, baselink: str):
    log(f'Registering "{title}" to database')
    item = Watchables(title=title, year=year, episodes=0, baselink=baselink,
                      datetimeadded=datetime.datetime.today(),
                      lastupdate=datetime.datetime.today())
    with get_session() as session:
        session.add(item)
        session.commit()
        item_status = Status(id=item.id, status='new', progress=0.0, location='',
                             lastupdate=datetime.datetime.today())
        session.add(item_status)
        session.commit()


if __name__ == '__main__':
    register('My ID Is Gangnam Beauty', 2018, 'https://www12.watchasian.co/my-id-is-gangnam-beauty-episode-1.html')
