import time
import urllib.request
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Retrieving the basic input stuffs
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 ' \
             '(KHTML, like Gecko) Maxthon/5.1.2.3000 Chrome/55.0.2883.75 Safari/537.36'
website = 'https://www13.watchasian.co/my-id-is-gangnam-beauty-episode-1.html'


def get_providers(baselink: str) -> dict:
    req = urllib.request.Request(baselink, headers={'User-Agent': USER_AGENT})
    r = urllib.request.urlopen(req)
    bytecode = r.read()
    htmlstr = bytecode.decode()
    soup = BeautifulSoup(htmlstr, 'html.parser')

    providers = {}
    one_set_streamers = soup.find(attrs={'class': 'anime_muti_link'})
    for streamer in one_set_streamers.find_all('li'):
        streamer_name = ' '.join(streamer['class'])
        vid_link = streamer['data-video']
        if 'http' not in vid_link:
            vid_link = f'https:{vid_link}'
        providers[streamer_name] = vid_link
    return providers


def getembed_from_watchasian(embed_link: str, provider: str) -> str:
    getembed = {'streamango': getembed_streamango,
                'kvid': getembed_kvid,
                'openload': getembed_openload,
                'mp4upload': getembed_mp4upload,
                'xstreamcdn': getembed_xstreamcdn,
                'thevideo': getembed_thevideo}
    return getembed[provider](embed_link)


def getembed_streamango(link: str) -> str:
    # https://bearberry.fruithosted.net/dl/n/Scd1S42YY-_9kS7x/eemoleqdqflrqqfm/lWPwCrUGdDpM9MIur8_ZY0lpoea4uXNZAVu15q0r91I3iU-DwtHDJpH7g9zSWX0MS0RiroSfBJ4ukGHafsh_6r4JcqsGQWH03CAAaVA0crSFOVa-xFyxmC2dEhyft177HB1k-xc0ptpFaXHoGIJ5snG_6yazWYxfmHCU--lqIK72fhnSBQ7kn8xSzhCjV50VaFgh_nN20Bc4k49s8R11yg_oD2hLcTAXqa3Wd25XliRpkqd5oxwtlU42wm9zKwMkdYixLZw5q7MvWXCDzdrppY6xDCfbk3c6HjTWVkMC_8QwLotslpDiUfx-nkH8ccBFec10B6dAzCHmV9DqMvhcjdhNqtd53FiauDPWPFo9HoNvzoSC-DpbX6DMns4mmVvW6EQBKDo1tDg5BR5v6__5SBglwOY5740n7tUn8NFlV80/drama_147741.mp4
    # profile = webdriver.FirefoxProfile()
    # Set a user agent string to help parse webserver logs easily
    # profile.set_preference("general.useragent.override", "Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 selenium.py")
    fox_opt = webdriver.FirefoxOptions()
    fox_opt.add_argument('--headless')
    driver = webdriver.Firefox(options=fox_opt)
    try:
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
    except WebDriverException as wde:
        raise LookupError(wde.msg)
    finally:
        driver.quit()
    return vid_link


def getembed_openload(link: str) -> str:
    fox_opt = webdriver.FirefoxOptions()
    fox_opt.add_argument('--headless')
    driver = webdriver.Firefox(options=fox_opt)
    driver.get(link)
    dl_link = driver.find_element_by_css_selector('#DtsBlkVFQx').get_attribute('textContent')
    print(dl_link)
    driver.quit()
    temp_link = "https://openload.co" + "/stream/" + dl_link
    print(temp_link)
    full_link = requests.get(temp_link, allow_redirects=False)
    temp_link = full_link.headers['location']
    return temp_link


def getembed_mp4upload(link: str) -> str:
    print(f'Finding video link from mp4upload page <{link}>...')
    fox_opt = webdriver.FirefoxOptions()
    fox_opt.add_argument('--headless')
    driver = webdriver.Firefox(options=fox_opt)
    try:
        driver.get(link)
        dl_link = driver.find_element_by_id('vid_html5_api').get_attribute('src')
        return dl_link
    finally:
        driver.quit()


def getembed_xstreamcdn(link: str) -> str:
    print(f'Finding video link from xstreamcdn page <{link}>...')
    fox_opt = webdriver.FirefoxOptions()
    fox_opt.add_argument('--headless')
    driver = webdriver.Firefox(options=fox_opt)
    try:
        driver.get(link)
        driver.find_element_by_tag_name('body').click()
        time.sleep(1)
        driver.find_element_by_tag_name('body').click()
        time.sleep(1)
        driver.find_element_by_tag_name('body').click()
        dl_link = driver.find_element_by_tag_name('video').get_attribute('src')
        full_link = requests.get(dl_link, allow_redirects=False)
        temp_link = full_link.headers['location']
        return temp_link
    finally:
        driver.quit()


def getembed_thevideo(link: str) -> str:
    print(f'Finding video link from thevideo page <{link}>...')
    fox_opt = webdriver.FirefoxOptions()
    fox_opt.add_argument('--headless')
    driver = webdriver.Firefox(options=fox_opt)
    try:
        driver.get(link)
        # time.sleep(3)
        video_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
        dl_link = video_element.get_attribute('src')
        # full_link = requests.get(dl_link, allow_redirects=False)
        # temp_link = full_link.headers['location']
        return dl_link
    finally:
        driver.quit()


def getembed_kvid(link: str) -> str:
    fox_opt = webdriver.FirefoxOptions()
    fox_opt.add_argument('--headless')
    driver = webdriver.Firefox(options=fox_opt)
    try:
        driver.get(link)
        video_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
        dl_link = video_element.get_attribute('src')
        x = 0
        while dl_link == '' or x < 3:
            driver.find_element_by_tag_name('body').click()
            # video_element.click()
            # time.sleep(0.2)
            dl_link = video_element.get_attribute('src')
            x += 1
        if dl_link == '':
            raise LookupError('kvid: no video src found')
        return dl_link
    finally:
        driver.quit()


def getembed_kvid_old(link: str) -> str:
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
        raise LookupError('no mp4 link available')


if __name__ == "__main__":
    # qw = get_providers('https://www13.watchasian.co/please-come-back-mister-episode-12.html')
    # for q in qw:
    #     print(f'{q}: {qw[q]}')
    link = getembed_xstreamcdn('https://gcloud.live/v/7y9wg658xoj')
    print(link)
