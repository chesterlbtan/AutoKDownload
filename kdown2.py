
from data.settings import LOG_FOLDER, TICKET_FOLDER, DOWNLOAD_FOLDER
import datetime
import glob
import logging
import os
import urllib.request
from urllib.error import URLError
import requests
import shutil

# Initialize logger
if not os.path.exists(LOG_FOLDER):
    os.mkdir(LOG_FOLDER)
LOG_FILE = os.path.join(LOG_FOLDER, f"kdown2Log_{datetime.date.today().strftime('%Y%m%d')}.log")
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


def move_to_folder(origfile: str, folder: str):
    file_basename = os.path.basename(origfile)
    stage2_path = os.path.join(TICKET_FOLDER, folder)
    if not os.path.exists(stage2_path):
        os.mkdir(stage2_path)
    new_fullpath = os.path.join(stage2_path, file_basename)
    shutil.copy2(origfile, new_fullpath)


def main():
    log("Let's start downloading!!")
    log("")
    tickets = glob.glob(os.path.join(TICKET_FOLDER, '*.txt'))
    if len(tickets) > 0:
        log(f'processing ticket id: {tickets[0]}')
        with open(tickets[0], 'r') as fr:
            info = fr.read().split('\t')
        series = info[0]
        ep_num = info[1]
        folder = info[2]
        dl_link = info[4]
        dl_fullname = os.path.join(DOWNLOAD_FOLDER, folder)
        if not os.path.exists(dl_fullname):
            os.mkdir(dl_fullname)
        dl_fullname = os.path.join(dl_fullname, f'{series} Episode {ep_num}.mp4')

        try:
            xxx = download_video(dl_link, dl_fullname)
            log(f'done downloading {xxx}')
        except URLError as ex:
            # ex.reason can only be retrieved once
            url_err_msg = str(ex.reason)
            log(url_err_msg)
            if 'SSL: CERTIFICATE_VERIFY_FAILED' in url_err_msg:
                log('invalid video link, we will move this ticket to stage2 folder')
                move_to_folder(tickets[0], 'stage2')
            elif 'Forbidden' in url_err_msg:
                log('video link has expired, this ticket need to be regenerated')
                move_to_folder(tickets[0], 'forbidden')
            else:
                log('unknown error')
                move_to_folder(tickets[0], 'error')
        os.remove(tickets[0])
        return True
    else:
        log('no files found...')
        return False


if __name__ == "__main__":
    try:
        while main():
            log('next...')
    except Exception as err:
        logging.error(err)
