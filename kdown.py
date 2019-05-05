from data.settings import LOG_FOLDER, DOWNLOAD_FOLDER
import datetime
import logging
import os
import urllib.request
from urllib.error import URLError
import requests
import subprocess
import time
from sqlalchemy import func
from typing import List

from anghari_db import Watchables, Status, Episodes, get_session
from utils.download import getvidlink_from_watchasian

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


def download_video(dl_link: str, dl_name: str):
    log(f'accessing link: {dl_link}')
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
    c_size = 0
    l_size = 0
    xt = datetime.datetime.now()
    with open(dl_name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=ch_sz):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                c_size = c_size + ch_sz
                # f.flush() commented by recommendation from J.F.Sebastian
            if (datetime.datetime.now() - xt).total_seconds() > 30:
                speed = (c_size - l_size) / (datetime.datetime.now() - xt).total_seconds() / 1000
                log(f'[{c_size / size * 100} %] {c_size / 1000000} of {size / 1000000} MB, {speed}kb/sec')
                xt = datetime.datetime.now()
                l_size = c_size

    end = datetime.datetime.now()
    duration = end - start
    log(f'downloading took {duration.total_seconds()} seconds')
    log(f'ended at {end.strftime("%c")}')
    return dl_name


def handle_new():
    with get_session() as session:
        tickets: List[Episodes] = session.query(Episodes).filter(Episodes.status == 'new').all()
    log(f'found {len(tickets)} links to download')
    for ticket in tickets:
        started = time.time()
        with get_session() as session:
            base_info: Watchables = session.query(Watchables).filter(Watchables.id == ticket.id).first()
            status_info: Status = session.query(Status).filter(Status.id == ticket.id).first()
        log(f'processing {base_info.title} Episode {ticket.episode}')
        if status_info.location == '':
            base_path = os.path.join(os.path.abspath(DOWNLOAD_FOLDER), f'[{base_info.year}] - {base_info.title}')
            with get_session() as session:
                session.query(Status).\
                    filter(Status.id == ticket.id).\
                    update({Status.location: base_path, Status.lastupdate: datetime.datetime.today()},
                           synchronize_session=False)
                session.commit()
        else:
            base_path = status_info.location
        if not os.path.exists(base_path):
            os.mkdir(base_path)
        dl_fullname = os.path.join(base_path, f'{base_info.title} Episode {ticket.episode}.mp4')

        try:
            providers = ['streamango', 'kvid']
            for prov in providers:
                try:
                    new_link = getvidlink_from_watchasian(ticket.base_link, prov)
                    break
                except LookupError:
                    log(f'fail to get {prov} link...')

            with get_session() as session:
                session.query(Episodes).\
                    filter(Episodes.episodes_id == ticket.episodes_id).\
                    update({Episodes.download_link: new_link, Episodes.lastupdate: datetime.datetime.today()},
                           synchronize_session=False)
                session.commit()
            ticket.download_link = new_link
            xxx = download_video(ticket.download_link, dl_fullname)
            log(f'Download success for {xxx}')
        except URLError as ex:
            # ex.reason can only be retrieved once
            url_err_msg = str(ex.reason)
            log(url_err_msg)
            if 'SSL: CERTIFICATE_VERIFY_FAILED' in url_err_msg:
                log('invalid video link, we will move this ticket to stage2 folder')
                with get_session() as session:
                    session.query(Episodes).\
                        filter(Episodes.episodes_id == ticket.episodes_id).\
                        update({Episodes.status: 'hls', Episodes.lastupdate: datetime.datetime.today()},
                               synchronize_session=False)
                    session.commit()
            elif 'Forbidden' in url_err_msg:
                log('video link has expired, this ticket need to be regenerated')
                with get_session() as session:
                    session.query(Episodes).\
                        filter(Episodes.episodes_id == ticket.episodes_id).\
                        update({Episodes.status: 'forbidden', Episodes.lastupdate: datetime.datetime.today()},
                               synchronize_session=False)
                    session.commit()
            else:
                log('unknown error')
                with get_session() as session:
                    session.query(Episodes).\
                        filter(Episodes.episodes_id == ticket.episodes_id).\
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
            session.query(Episodes).\
                filter(Episodes.episodes_id == ticket.episodes_id).\
                update({Episodes.download_link: new_link,
                        Episodes.status: 'new',
                        Episodes.lastupdate: datetime.datetime.today()}, synchronize_session=False)
            session.commit()
        log(f'Download update.')


def handle_hls():
    with get_session() as session:
        tickets: List[Episodes] = session.query(Episodes).filter(Episodes.status == 'hls').all()
    log(f'found {len(tickets)} hls links to download')
    for ticket in tickets:
        started = time.time()
        base_info: Watchables = session.query(Watchables).filter(Watchables.id == ticket.id).first()
        status_info: Status = session.query(Status).filter(Status.id == ticket.id).first()

        link_to_dl = ticket.download_link
        vid_name = os.path.join(status_info.location, f'{base_info.title} Episode {ticket.episode}.mp4')
        log(f'HLS download on page <{link_to_dl}>...')
        # ffmpeg -headers "Referer: https://embed.watchasian.co" -i "url" -c copy -bsf:a aac_adtstoasc "output.mp4"
        # cmd = f'ffmpeg -i "{link_to_dl}" -c copy -bsf:a aac_adtstoasc "{vid_name}"'
        cmd = f'ffmpeg -headers "Referer: https://embed.watchasian.co" -i "{link_to_dl}" -c copy "{vid_name}"'
        log(cmd)
        subprocess.call(cmd, shell=True)
        # os.system(cmd)

        ended = time.time()
        duration = ended - started

        if os.path.exists(vid_name):
            size = os.path.getsize(vid_name)
            with get_session() as session:
                session.query(Episodes). \
                    filter(Episodes.episodes_id == ticket.episodes_id). \
                    update({Episodes.status: 'done', Episodes.location: vid_name, Episodes.progress: 100.0,
                            Episodes.size: size, Episodes.duration: duration,
                            Episodes.lastupdate: datetime.datetime.today()},
                           synchronize_session=False)
                session.commit()


def main():
    log("Let's start downloading!!")
    log("")
    handle_new()
    handle_forbidden()
    handle_hls()


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        logging.error(err)
