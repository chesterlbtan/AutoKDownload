import time
import urllib.request
from bs4 import BeautifulSoup
from selenium import webdriver

# Retrieving the basic input stuffs
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 ' \
             '(KHTML, like Gecko) Maxthon/5.1.2.3000 Chrome/55.0.2883.75 Safari/537.36'
website = 'https://www13.watchasian.co/my-id-is-gangnam-beauty-episode-1.html'


def getvidlink_from_watchasian(baselink: str, provider: str) -> str:
    req = urllib.request.Request(baselink, headers={'User-Agent': USER_AGENT})
    r = urllib.request.urlopen(req)
    bytecode = r.read()
    htmlstr = bytecode.decode()
    soup = BeautifulSoup(htmlstr, 'html.parser')

    one_set_streamers = soup.find(attrs={'class': 'anime_muti_link'})
    for streamer in one_set_streamers.find_all('li'):
        streamer_name = ' '.join(streamer['class'])
        vid_link = streamer['data-video']
        print(f'{streamer_name}: {vid_link}')
        if streamer_name in provider:
            embed_link = vid_link
    if embed_link is None or embed_link == '':
        print(f'{provider} not found from the list')
        raise LookupError(f'{provider} not found from the list')

    if 'http' not in embed_link:
        embed_link = f'https:{embed_link}'
    print(embed_link)
    getembed = {'streamango': getembed_streamango, 'kvid': getembed_kvid}
    return getembed[provider](embed_link)


def getembed_streamango(link: str) -> str:
    # https://bearberry.fruithosted.net/dl/n/Scd1S42YY-_9kS7x/eemoleqdqflrqqfm/lWPwCrUGdDpM9MIur8_ZY0lpoea4uXNZAVu15q0r91I3iU-DwtHDJpH7g9zSWX0MS0RiroSfBJ4ukGHafsh_6r4JcqsGQWH03CAAaVA0crSFOVa-xFyxmC2dEhyft177HB1k-xc0ptpFaXHoGIJ5snG_6yazWYxfmHCU--lqIK72fhnSBQ7kn8xSzhCjV50VaFgh_nN20Bc4k49s8R11yg_oD2hLcTAXqa3Wd25XliRpkqd5oxwtlU42wm9zKwMkdYixLZw5q7MvWXCDzdrppY6xDCfbk3c6HjTWVkMC_8QwLotslpDiUfx-nkH8ccBFec10B6dAzCHmV9DqMvhcjdhNqtd53FiauDPWPFo9HoNvzoSC-DpbX6DMns4mmVvW6EQBKDo1tDg5BR5v6__5SBglwOY5740n7tUn8NFlV80/drama_147741.mp4
    # profile = webdriver.FirefoxProfile()
    # Set a user agent string to help parse webserver logs easily
    # profile.set_preference("general.useragent.override", "Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 selenium.py")
    driver = webdriver.Firefox()
    driver.get(link)
    embed_html = driver.page_source
    embed_soup = BeautifulSoup(embed_html, 'html.parser')
    video_tag = embed_soup.find(id='mgvideo_html5_api')
    print(video_tag['src'])

    vid_link = video_tag['src']
    if 'http' not in vid_link:
        vid_link = f'https:{vid_link}'
    print(vid_link)
    driver.get(vid_link)
    time.sleep(2)
    vid_link = driver.current_url
    driver.quit()
    return vid_link


def getembed_kvid(link: str) -> str:
    print(f'Finding video link from kvid page <{link}>...')
    header = {'User-Agent': USER_AGENT}
    req = urllib.request.Request(link, None, header)
    r = urllib.request.urlopen(req)
    bytecode = r.read()
    htmlstr = bytecode.decode()

    vid_link = []
    found_source = False
    for html_line in htmlstr.split('\n'):
        if 'playerInstance.setup' in html_line:
            found_source = True
        if found_source:
            if 'sources' in html_line:
                st = html_line.find('file: ')
                ed = html_line.find(',label:')
                vid_link.append(html_line[st + 7:ed - 1])
            if '});' in html_line:
                found_source = False

    print(vid_link)
    if len(vid_link) == 1:
        return vid_link[0]
    else:
        for vlink in vid_link:
            if '.mp4' in vlink:
                return vlink
