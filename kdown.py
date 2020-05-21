from data.settings import LOG_FOLDER, DOWNLOAD_FOLDER
import datetime
import logging
import os
import urllib.request
from urllib.error import URLError
import requests
import subprocess
import time
import tqdm
from sqlalchemy import func
from typing import List

from anghari_db import Watchables, Status, Episodes, get_session
from utils.download import getembed_from_watchasian, get_providers

# Initialize logger
if not os.path.exists(LOG_FOLDER):
    os.mkdir(LOG_FOLDER)
LOG_FILE = os.path.join(LOG_FOLDER, f"kdownLog_{datetime.date.today().strftime('%Y%m%d')}.log")
logging.basicConfig(filename=LOG_FILE, format='[%(asctime)s.%(msecs)03d] %(message)s',
                    datefmt=logging.Formatter.default_time_format, level=logging.INFO)
logging.info(f'Logger initialized in {LOG_FILE}')

# Ensure download folder is available
if not os.path.exists(DOWNLOAD_FOLDER):
    os.mkdir(DOWNLOAD_FOLDER)


def log(message: str):
    print(message)
    logging.info(message)


def download_openload_file(url, filename=None, csize=1000, quiet=False):
    r = requests.get(url, stream=True)
    file_size = int(r.headers["Content-Length"])
    if filename is None:
        filename = r.url.split("/")[-1]
    first_byte = 0
    r = requests.get(
        url, headers={"Range": "bytes=%s-%s" % (first_byte, file_size)}, stream=True
    )
    with tqdm.tqdm(
        total=file_size,
        initial=first_byte,
        unit="B",
        unit_scale=True,
        desc=filename[0:6] + "..." + filename[-7:],
        disable=quiet,
    ) as pbar:
        with open(filename, "wb") as fp:
            for chunk in r.iter_content(chunk_size=csize):
                fp.write(chunk)
                pbar.update(csize)
    return filename


def download_video(dl_link: str, dl_name: str):
    log(f'accessing link: {dl_link}')
    if dl_link.startswith('blob:'):
        ff = requests.get(dl_link)
        with open(dl_name, 'wb') as f:
            f.write(ff.content)
        return

    f = urllib.request.urlopen(dl_link)
    if "Content-Length" in f.headers:
        size = int(f.headers["Content-Length"])
        log(f'total video size: {size} bytes')
    else:
        size = -1
        log('size not indicated')
    start = datetime.datetime.now()
    log(f"started downloading {dl_name} at {start.strftime('%c')}")
    log(f'file size: {size}')

    r = requests.get(dl_link, stream=True)
    ch_sz = 1024
    with tqdm.tqdm(
        total=size,
        initial=0,
        unit="B",
        unit_scale=True,
        desc=dl_name[0:6] + "..." + dl_name[-7:],
        disable=False,
    ) as pbar:
        with open(dl_name, 'wb') as f:
            for chunk in r.iter_content(chunk_size=ch_sz):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush() commented by recommendation from J.F.Sebastian
                    pbar.update(ch_sz)
    end = datetime.datetime.now()
    duration = end - start
    log(f'downloading took {duration.total_seconds()} seconds')
    log(f'ended at {end.strftime("%c")}')
    return dl_name


def get_dl_link(dctlinks: dict, wanted: str):
    if wanted not in dctlinks.keys():
        log(f'No [{wanted}] link found...')
        raise LookupError
    try:
        new_link = getembed_from_watchasian(dctlinks[wanted], wanted)
        log(f'successfully retrieve link from {wanted}: {new_link}')
        return new_link
    except Exception as ex:
        log(f'Failed to get [{wanted}] link...')
        logging.error(ex)
        raise ex


def handle_new():
    with get_session() as session:
        tickets: List[Episodes] = session.query(Episodes).filter(Episodes.status == 'new').all()
    log(f'found {len(tickets)} links to download')
    for ticket in tickets:
        started = time.time()
        with get_session() as session:
            base_info: Watchables = session.query(Watchables).filter(Watchables.id == ticket.id).first()
            status_info: Status = session.query(Status).filter(Status.id == ticket.id).first()
        log(f'')
        log(f'processing {base_info.title} Episode {ticket.episode}')
        if status_info.location == '':
            base_path = os.path.join(os.path.abspath(DOWNLOAD_FOLDER), f'[{base_info.year}] - {base_info.title}')
            with get_session() as session:
                session.query(Status). \
                    filter(Status.id == ticket.id). \
                    update({Status.location: base_path, Status.lastupdate: datetime.datetime.today()},
                           synchronize_session=False)
                session.commit()
        else:
            base_path = status_info.location
        if not os.path.exists(base_path):
            os.mkdir(base_path)
        dl_fullname = os.path.join(base_path, f'{base_info.title} Episode {ticket.episode}.mp4')

        try:
            providers = get_providers(ticket.base_link)
            # print the providers for debugging
            for src in providers:
                log(f'{src}: {providers[src]}')

            wanted_prov = ['xstreamcdn', 'kvid', 'streamango', 'openload', 'thevideo', 'mp4upload']
            for prov in wanted_prov:
                try:
                    new_link = get_dl_link(providers, prov)
                except Exception as geterr:
                    logging.exception(geterr)
                    continue

                try:
                    with get_session() as session:
                        session.query(Episodes). \
                            filter(Episodes.episodes_id == ticket.episodes_id). \
                            update({Episodes.download_link: new_link, Episodes.lastupdate: datetime.datetime.today()},
                                   synchronize_session=False)
                        session.commit()
                    ticket.download_link = new_link
                    if prov == 'openload':
                        xxx = download_openload_file(ticket.download_link, dl_fullname)
                    else:
                        try:
                            xxx = download_video(ticket.download_link, dl_fullname)
                        except:
                            xxx = download_openload_file(ticket.download_link, dl_fullname)
                    log(f'Download success for {xxx}')
                    break
                except requests.exceptions.ChunkedEncodingError:
                    log('Connection Reset Error, ChunkedEncodingError')
                    if prov == wanted_prov[-1]:
                        raise
        except URLError as ex:
            # ex.reason can only be retrieved once
            url_err_msg = str(ex.reason)
            log(url_err_msg)
            if 'Forbidden' in url_err_msg:
                log('video link has expired, this ticket need to be regenerated')
                with get_session() as session:
                    session.query(Episodes). \
                        filter(Episodes.episodes_id == ticket.episodes_id). \
                        update({Episodes.status: 'forbidden', Episodes.lastupdate: datetime.datetime.today()},
                               synchronize_session=False)
                    session.commit()
            else:
                log('unknown error')
                with get_session() as session:
                    session.query(Episodes). \
                        filter(Episodes.episodes_id == ticket.episodes_id). \
                        update({Episodes.status: 'dl error', Episodes.lastupdate: datetime.datetime.today()},
                               synchronize_session=False)
                    session.commit()
        except Exception as kew:
            logging.exception(kew)
            continue
        else:
            ended = time.time()
            duration = ended - started
            size = os.path.getsize(dl_fullname)
            with get_session() as session:
                # update the Episodes table
                session.query(Episodes). \
                    filter(Episodes.episodes_id == ticket.episodes_id). \
                    update({Episodes.status: 'done', Episodes.location: dl_fullname, Episodes.progress: 100.0,
                            Episodes.size: size, Episodes.duration: duration,
                            Episodes.lastupdate: datetime.datetime.today()},
                           synchronize_session=False)
                session.commit()

                # update the Status table
                numerator = session.query(func.count(Episodes.status)). \
                    filter(Episodes.id == ticket.id).filter(Episodes.status == 'done').first()
                denominator = session.query(func.count(Episodes.status)).filter(Episodes.id == ticket.id).first()
                print(f'{numerator} / {denominator}')
                epp = numerator[0] / denominator[0] * 100
                update_dict = {Status.progress: epp}
                if numerator[0] == denominator[0]:
                    update_dict[Status.status] = 'done'
                session.query(Status).filter(Status.id == ticket.id). \
                    update(update_dict, synchronize_session=False)
                session.commit()


def handle_forbidden():
    with get_session() as session:
        tickets: List[Episodes] = session.query(Episodes).filter(Episodes.status == 'forbidden').all()
    log(f'found {len(tickets)} forbidden links to refresh')
    for ticket in tickets:
        with get_session() as session:
            base_info: Watchables = session.query(Watchables).filter(Watchables.id == ticket.id).first()
        log(f'refreshing {base_info.title} Episode {ticket.episode}')

        from divide import get_video_link
        new_link = get_video_link(ticket.base_link)
        with get_session() as session:
            session.query(Episodes). \
                filter(Episodes.episodes_id == ticket.episodes_id). \
                update({Episodes.download_link: new_link,
                        Episodes.status: 'new',
                        Episodes.lastupdate: datetime.datetime.today()}, synchronize_session=False)
            session.commit()
        log(f'Download update.')


def main():
    log("Let's start downloading!!")
    log("")
    handle_new()
    # handle_forbidden()


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        logging.error(err)
