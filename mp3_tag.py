import acoustid
import musicbrainzngs
import requests
import re
from bs4 import BeautifulSoup
import os
from time import sleep
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, USLT, error
from mutagen.easyid3 import EasyID3
import mutagen.id3
import sys
from sys import argv
from tqdm import tqdm

musicbrainzngs.set_useragent('tagger','0.1',contact=None)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
colorama.inti()

#add your acoustid key by making a profile
acoustid_key='' 

#gen audiofingerprint and get data from acoustid
def fingerprint(fn):
    art_til=[]
    alb=[]
    count=0
    result=acoustid.match(acoustid_key,fn,parse=False)
    album_result=acoustid.match(acoustid_key,fn,meta='releasegroups',parse=False)
    print(bcolors.WARNING+f'Select a Title and Artist for {fn}'+bcolors.ENDC)
    try:
        for x in result['results']:
            for y in x['recordings']:
                artlist=[x['name'] for x in y['artists']]
                if len(artlist)>1:
                    temp_title=y['title']+(' (feat. ')+''.join(p for p in artlist[1:])+')'
                else:
                    temp_title=y['title']
                art_til.append([artlist[0],temp_title])
            for x in art_til:
                print(str(count)+'. '+x[0]+' - '+x[1])
                count=count+1
    except Exception:
        pass
    print(str(count)+'. Manual Entry')
    while True:
        try:
            user_choice=int(input('>  '))
            if user_choice in range(count+1):
                break
            else:
                continue
        except ValueError:
            continue
    if user_choice==count:
        artist=str(input("Enter the exact artist name:  "))
        title=str(input('Enter the exact title:  '))
    else:
        artist=art_til[user_choice][0]
        title=art_til[user_choice][1]
        count=0
    print(bcolors.WARNING+f'Select an Album name for {fn}'+bcolors.ENDC)
    try:
        for x in album_result['results']:
            for y in x['releasegroups']:
                if 'Music From the Motion Picture' in y['title']:
                    alb_title=y['title'].split(':')[0]+' ('+str(y['title'].split(':')[1]).strip()+')'
                else:
                    alb_title=y['title']
                print(str(count)+'. '+alb_title+' - '+y['type'])
                alb.append([alb_title,y['id'],y['type']])
                count=count+1
    except Exception:
        pass
    print(str(count)+'. Manual Entry')
    while True:
        try:
            user_choice=int(input('>  '))
            if user_choice in range(count+1):
                break
            else:
                continue
        except ValueError:
            continue
    if user_choice==count:
        album=str(input("Enter the exact album name:  "))
        mbid=None
        atype=None
    else:
        album=alb[user_choice][0]
        mbid=alb[user_choice][1]
        atype=alb[user_choice][2]
    if mbid is not None:
        date=musicbrainzngs.get_release_group_by_id(mbid)['release-group']['first-release-date'][0:5]
    else:
        date=None
    return artist,title,album,mbid,date,atype


def get_lyrics(artist,title):
    try:
        artist = artist.replace(' ', '_').lower().replace('&', '%26').strip('_').replace('\'', '%27')
        if 'feat' in title:
            title = title.split('feat')[0]
        title = title.replace(' ', '_').lower().strip('_')
        url = f'http://lyrics.wikia.com/wiki/{artist}:{title}'
        soup = BeautifulSoup(requests.get(url).text, 'html.parser')
        a = soup.find('div', attrs={'class': 'lyricbox'})
        lyrics = str(a).replace('<br/>', '\n').replace('<div class="lyricbox">', '').replace('<div class="lyricsbreak"></div>', '').replace('</div>', '')
        return lyrics
    except Exception:
        return 'None'

def get_cover_art(mbid):
    def custom_album_art():
        try:
            os.remove('download.jpg')
        except Exception:
            pass
        while(not os.path.exists('download.jpg')):
            input('Download cover art and save as \"download.jpg\". Press enter to continue..> ')
    if mbid is not None:
        r=requests.get(f'http://coverartarchive.org/release-group/{mbid}/front',stream=True)
        with open('download.jpg','wb') as f:
            for x in tqdm(r.iter_content(),total=int(r.headers['content-length']),dynamic_ncols=True,desc=bcolors.WARNING+'Downloading Cover Art'+bcolors.ENDC,unit='bytes'):
                f.write(x)
        os.system('open download.jpg')
        sleep(3)
        user_choice=input('Is the cover image correct or would you like to provide your own?(y/n) > ')
        while(user_choice not in ('y','n')):
            user_choice=input('> ')
        if user_choice=='y':
            pass
        else:
            custom_album_art()
    else:
        custom_album_art()
    
def tag_file(fn,artist,album,title,lyrics,date,atype):
    try:
        audiofile=MP3(fn,ID3=EasyID3)
        audiofile.delete()
        audiofile.save()
        audiofile['title']=title
        audiofile['album']=album
        audiofile['artist']=artist
        audiofile['albumartist']=artist
        if date is not None:
            audiofile['date']=date
        audiofile['discnumber']=['1/1']
        if atype=='Single':
            audiofile['tracknumber']=['1/1']
        audiofile.save()
        audiofile=MP3(fn,ID3=ID3)
        audiofile.tags.add(APIC(encoding=3,mime='image/jpeg',type=3,desc=u'Cover',data=open('download.jpg','rb').read()))
        if lyrics is not None:
            audiofile.tags.add(USLT(lang='eng',text=lyrics))
        audiofile.save()
        os.rename(fn,artist+' - '+title+'.mp3')
        os.remove('download.jpg')
        return(True)
    except Exception:
        return(False)

try:
    if argv[1]:
        argv_flag=1
except Exception:
    argv_flag=0


try:
    files_added=0
    if argv_flag==1:
        if argv[1] in os.listdir():
            mp3_files=[argv[1]]
        else:
            print(bcolors.FAIL+'File passed in argument doesn\'t exists. Exiting'+bcolors.ENDC)
            sys.exit(0)
    else:
        mp3_files=[x for x in os.listdir() if x[-4:]=='.mp3']
    if len(mp3_files)>0:
        for fn in mp3_files:
            artist,title,album,mbid,date,atype=fingerprint(fn)
            get_cover_art(mbid)
            lyrics=get_lyrics(artist,title)
            if lyrics is None:
                print(bcolors.FAIL+'Could not find Lyrics. Please manually add it..'+bcolors.ENDC)
            else:
                print(bcolors.OKGREEN+'Lyrics found'+bcolors.ENDC)
            if tag_file(fn,artist,album,title,lyrics,date,atype):
                print(bcolors.OKGREEN+'Audio file successfully tagged'+bcolors.ENDC)
            print(mbid)
            files_added=files_added+1
        print(bcolors.OKBLUE+f'Total Files Processed: {files_added}'+bcolors.ENDC)
    else:
        print(bcolors.WARNING+'No MP3 file given.'+bcolors.ENDC)
except KeyboardInterrupt:
    print('\n')
    sys.exit(0)
except Exception:
    print(bcolors.FAIL+'AN ERROR OCCURED'+bcolors.ENDC)
    raise