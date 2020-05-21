
from data.settings import TICKET_FOLDER, LOG_FOLDER, USER_AGENT
import datetime
import logging
import os
import urllib.request
from anghari_db import Watchables, Status, Episodes, get_session

# Initialize logger
if not os.path.exists(LOG_FOLDER):
    os.mkdir(LOG_FOLDER)
LOG_FILE = os.path.join(LOG_FOLDER, f"generatorLog_{datetime.date.today().strftime('%Y%m%d')}.log")
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


def get_video_link(site: str, source: str = None) -> str:
    log(f'Finding video link from page <{site}>...')
    header = {'User-Agent': USER_AGENT}
    req = urllib.request.Request(site, None, header)
    r = urllib.request.urlopen(req)
    bytecode = r.read()
    htmlstr = bytecode.decode()

    scnd_set = []
    if source is None:
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
        embed_link = 'https:' + scnd_set[1][start + 5:end - 1]
    else:
        streamer_list = False
        for html_line in htmlstr.split('\n'):
            if '<div class="anime_muti_link"' in html_line:
                streamer_list = True
            if streamer_list and '<li class=' in html_line:
                ind_s = html_line.find('<li class=') + 11
                ind_e = html_line.find(' rel') - 1
                streamer_name = html_line[ind_s:ind_e]
                log(f'streamer name: {streamer_name}')
                if source in streamer_name:
                    ind_s = html_line.find('data-video=') + 12
                    ind_e = html_line.find('">')
                    embed_link = html_line[ind_s:ind_e]
                    break
    return get_from_embed(embed_link)


def divide():
    with get_session() as session:
        rows = session.query(Watchables).\
            join(Status).\
            filter(Status.status == 'new').\
            all()
    header = {'User-Agent': USER_AGENT}
    for row in rows:
        print(row.title)
        req = urllib.request.Request(row.baselink, None, header)
        r = urllib.request.urlopen(req)
        bytecode = r.read()
        htmlstr = bytecode.decode()

        dct_episodes: {int, str} = {}
        base_link = str.join('/', row.baselink.split('/')[0:-1])
        found_list = False
        for html_line in htmlstr.split('\n'):
            if found_list:
                if '</select>' in html_line:
                    break
                ep_link = base_link + html_line[html_line.find('value="') + 7:html_line.find('">')]
                try:
                    ep_num = int(html_line[html_line.find('>Episode ') + 9:html_line.find('</option>')])
                except:
                    continue
                dct_episodes[ep_num] = ep_link
            elif '<select onchange' in html_line:
                found_list = True

        with get_session() as session:
            session.query(Watchables).\
                filter(Watchables.id == row.id).\
                update({Watchables.episodes: len(dct_episodes.keys())}, synchronize_session=False)
            for ep in dct_episodes.keys():
                print(ep)
                try:
                    dl_link = get_video_link(dct_episodes[ep], None)
                except:
                    dl_link = ''
                if dl_link is not None:
                    epi = Episodes(id=row.id, episode=ep, status='new',
                                   base_link=dct_episodes[ep],
                                   download_link=dl_link,
                                   progress=0.0, size=0,
                                   datetimeadded=datetime.datetime.today(),
                                   lastupdate=datetime.datetime.today())
                else:
                    epi = Episodes(id=row.id, episode=ep, status='error',
                                   base_link=dct_episodes[ep],
                                   download_link='error',
                                   progress=0.0, size=0,
                                   datetimeadded=datetime.datetime.today(),
                                   lastupdate=datetime.datetime.today())
                session.add(epi)
            session.query(Status).\
                filter(Status.id == row.id).\
                update({Status.status: 'in progress'}, synchronize_session=False)
            session.commit()


if __name__ == '__main__':
    divide()
