import re
import copy
import json
import string
import requests
import unicodedata
from bs4 import BeautifulSoup


soup_headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
              'AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/50.0.2661.102 Safari/537.36'}
cookies = {'birthtime': '631148401'}


words_subs = {'1': ['i', 'one', '1'], 'one': ['i', 'one', '1'], 'i': ['i', 'one', '1'],
              '2': ['ii', 'two', '2'], 'two': ['ii', 'two', '2'], 'ii': ['ii', 'two', '2'],
              '3': ['iii', 'three', '3'], 'three': ['iii', 'three', '3'], 'iii': ['iii', 'three', '3'],
              '4': ['iv', 'four', '4'], 'four': ['iv', 'four', '4'], 'iv': ['iv', 'four', '4'],
              '5': ['v', 'five', '5'], 'five': ['v', 'five', '5'], 'v': ['v', 'five', '5'],
              '6': ['vi', 'six', '6'], 'six': ['vi', 'six', '6'], 'vi': ['vi', 'six', '6'],
              '7': ['vii', 'seven', '7'], 'seven': ['vii', 'seven', '7'], 'vii': ['vii', 'seven', '7'],
              '8': ['viii', 'eight', '8'], 'eight': ['viii', 'eight', '8'], 'viii': ['viii', 'eight', '8'],
              '9': ['ix', 'nine', '9'], 'nine': ['ix', 'nine', '9'], 'ix': ['ix', 'nine', '9'],
              '10': ['x', 'ten', '10'], 'ten': ['x', 'ten', '10'], 'x': ['x', 'ten', '10']}


def format_string(str_obj):
    str_obj = str_obj.replace('&', 'and')
    title_words = [v.translate(str.maketrans('', '', string.punctuation))
                       .lower().strip() for v in re.sub('/|_|-|:|™|®', ' ', str_obj).split(' ')]
    title_words = [unicodedata.normalize('NFKD', v).encode('ASCII', 'ignore').decode('utf-8')
                   for v in title_words if v != '']
    return title_words


def get_best_match(candidates, title):
    best_match = 0
    best_index = 0
    best_score = 0

    title_words = format_string(title)
    
    for ind, candidate in enumerate(candidates):

        temp_candidate = candidate.replace('video game', '')
        candidate_words = format_string(temp_candidate)
        
        nb_common_words = 0
        if len(title_words) < len(candidate_words):
            smaller_title = title_words
            bigger_title = copy.copy(candidate_words)
        else:
            smaller_title = candidate_words
            bigger_title = copy.copy(title_words)

        for word in smaller_title:
            if word in bigger_title:
                nb_common_words += 1
                bigger_title.remove(word)
            elif word in words_subs:
                for sub_word in words_subs[word]:
                    if sub_word in bigger_title:
                        nb_common_words += 1
                        bigger_title.remove(sub_word)
        max_length = max(len(title_words), len(candidate_words))
        nb_smaller_words = nb_common_words / len(smaller_title)
        nb_common_words /= max_length

        # score = (nb_smaller_words + nb_common_words) / 2
        if nb_common_words > best_match:
            best_match = nb_common_words
            best_score = nb_smaller_words
            best_index = ind

    return best_index, best_match, best_score


def get_soup(url, steam=False):
    if steam:
        
        webpage = requests.get(url, headers=soup_headers, cookies=cookies)
    else:
        webpage = requests.get(url, headers=soup_headers)
    return BeautifulSoup(webpage.text, 'html.parser')


def get_dlgame_url(title):
    temp_title = title
    score = 0, 0
    url = '', ''
    success = True
    try:
        base_url = 'https://dlpsgame.com/?s='
        new_title = title.replace(' ', '+')
        url = base_url + new_title

        soup = get_soup(url)
        urls = []
        search_results = soup.findAll('div', {'class': ['post', 'bar', 'hentry']})[:10]
        candidates = []
        for result in search_results:
            search_title = result.find('h2', {'class': ['post-title', 'entry-title']}).text
            search_title = search_title.replace('\n', '')
            urls.append(result.find('a').attrs['href'])
            candidates.append(search_title)

        best_candidate = get_best_match(candidates, title)
        temp_title = candidates[best_candidate[0]]
        score = best_candidate[1]
        url = urls[best_candidate[0]]
        
    except Exception as _:
        success = False

    return {'dlgame-title': temp_title, 'dlgame-score': score,
            'dlgame-url': url,'dlgame-success': success}


def get_dlgame_info(url, score):
    dlgame_description = '#'
    success = True

    if float(score) >= 0.7:
        try:
            soup = get_soup(url)
            try:
                dlgame_description = soup.find('blockquote').text
            except Exception as _:
                dlgame_description = '#'
        except Exception as _:
            success = False
    else:
        success = False
    
    return {'dlgame-description': dlgame_description, 'dlgame-success': success}


if __name__ == '__main__':
    with open('ultimate_games.json', 'r', encoding='utf-8') as file:
        ultimate_games = json.load(file)

    count = 0
    for game in ultimate_games:
        best_dlgame = get_dlgame_url(game)
        if best_dlgame['dlgame-success']:
            count += 1
        print(count, game, '#', best_dlgame['dlgame-title'], best_dlgame['dlgame-success'], best_dlgame['dlgame-score'])