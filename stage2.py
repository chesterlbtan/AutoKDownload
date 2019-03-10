
from data.settings import TICKET_FOLDER, LOG_FOLDER, DOWNLOAD_FOLDER
import datetime
import glob
import logging
import os
import urllib.request
import requests
import shutil
import subprocess

# Initialize logger
if not os.path.exists(LOG_FOLDER):
    os.mkdir(LOG_FOLDER)
LOG_FILE = os.path.join(LOG_FOLDER, f"stage2Log_{datetime.date.today().strftime('%Y%m%d')}.log")
logging.basicConfig(filename=LOG_FILE, format='[%(asctime)s.%(msecs)03d] %(message)s',
                    datefmt=logging.Formatter.default_time_format, level=logging.INFO)
logging.info(f'Logger initialized in {LOG_FILE}')

# Ensure ticket folder is available
if not os.path.exists(TICKET_FOLDER):
    os.mkdir(TICKET_FOLDER)


def log(message: str):
    print(message)
    logging.info(message)


def get_from_embed(embed: str) -> str:
    log(f'Finding video link from embed page <{embed}>...')
    header = {'User-Agent': USER_AGENT}
    req = urllib.request.Request(embed, None, header)
    r = urllib.request.urlopen(req)
    bytecode = r.read()
    htmlstr = bytecode.decode()

    player_instance = []
    found_source = False
    for html_line in htmlstr.split('\n'):
        if 'playerInstance.setup' in html_line:
            found_source = True
        if found_source:
            player_instance.append(html_line)
            if '});' in html_line:
                break

    for jkp in player_instance:
        if 'sources' in jkp:
            st = jkp.find('file: ')
            ed = jkp.find(',label:')
            return jkp[st+7:ed-1]


def move_to_folder(origfile: str, folder: str):
    file_basename = os.path.basename(origfile)
    stage2_path = os.path.join(TICKET_FOLDER, folder)
    if not os.path.exists(stage2_path):
        os.mkdir(stage2_path)
    new_fullpath = os.path.join(stage2_path, file_basename)
    shutil.copy2(origfile, new_fullpath)


def get_video_link(site: str) -> str:
    log(f'Finding video link from page <{site}>...')
    header = {'User-Agent': USER_AGENT}
    req = urllib.request.Request(site, None, header)
    r = urllib.request.urlopen(req)
    bytecode = r.read()
    htmlstr = bytecode.decode()

    scnd_set = []
    found_iframe = False
    for html_line in htmlstr.split('\n'):
        if 'watch_video watch-iframe' in html_line:
            found_iframe = True
        if found_iframe:
            scnd_set.append(html_line)
            if '</div>' in html_line:
                break

    start = scnd_set[1].find('src="')
    end = scnd_set[1].find(' target=')
    embed_link: str = 'https:' + scnd_set[1][start + 5:end - 1]
    return get_from_embed(embed_link)


def tkt_maker(folder: str, name: str, episode: str, base_link: str):
    filename = f'{name} (ep{episode}).txt'
    log(f'generating ticket file: {filename}')
    dl_link = get_video_link(base_link)
    log(f'dl_link: {dl_link}')
    with open(os.path.join(TICKET_FOLDER, filename), 'w') as f:
        f.write(str.join('\t', [name, episode, folder, base_link, dl_link]))
    log('ticket created...')


def download_hls(link: str, vid_name: str):
    log(f'HLS download on page <{link}>...')
    # ffmpeg -headers "Referer: https://embed.watchasian.co" -i "url" -c copy -bsf:a aac_adtstoasc "output.mp4"
    cmd = f'ffmpeg -headers "Referer: https://embed.watchasian.co" -i "{link}" -c copy "{vid_name}"'
    log(cmd)
    # subprocess.call(cmd, shell=True)
    os.system(cmd)


def main():
    log('Getting new links in stage2 folder')
    log("")
    s2_tickets = glob.glob(os.path.join(TICKET_FOLDER, 'stage2', '*.txt'))
    for s2_tick in s2_tickets:
        log(f'processing ticket <{s2_tick}>')
        with open(s2_tick, 'r') as fr:
            info = fr.read().split('\t')
        series = info[0]
        ep_num = info[1]
        folder = info[2]
        base_link = info[3]
        dl_link = info[4]

        dl_fullname = os.path.join('.', DOWNLOAD_FOLDER, folder)
        if not os.path.exists(dl_fullname):
            os.mkdir(dl_fullname)
        dl_fullname = os.path.join(dl_fullname, f'{series} Episode {ep_num}.mp4')

        download_hls(dl_link, dl_fullname)
        log('done dl...')
        if not os.path.exists(dl_fullname):
            move_to_folder(s2_tick, 'error')
        os.remove(s2_tick)
        log('')


if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        logging.error(err)
