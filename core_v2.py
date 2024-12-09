import time

import pymongo
import json
import unicodedata
import string
import copy
import re
from bs4 import BeautifulSoup
import requests
from howlongtobeatpy import HowLongToBeat
from giantbomb import giantbomb
from datetime import datetime
from googlesearch import search


json_list = []
my_key = 'f0673d2f0d082808075c28853ecf492fe82f67a2'
rawg_key = '8a120bfae1b04e538ad87617801a5e2a'
gb = giantbomb.Api(my_key, 'API test')

alphabet = list(string.ascii_uppercase)
base_meta = 'https://www.metacritic.com'
base_wiki = 'https://en.wikipedia.org'
base_epic = 'https://www.epicgames.com'
base_riot = 'https://en.riotpixels.com/'
base_hltb = 'https://howlongtobeat.com/game/'
htlb_obj = HowLongToBeat()
download_images = True

names_dict = {'Giant Id': 'Giant Id', 'name': 'Name', 'aliases': 'Aliases', 'deck': 'GB Intro',
              'description': 'GB Description', 'platforms': 'Platforms', 'developers': 'Developers',
              'publishers': 'Publishers', 'franchises': 'Franchises', 'releases': 'Releases', 'images': 'Images',
              'genres': 'GB Genres', 'themes': 'Themes', 'original_release_date': 'GB Release Date',
              'videos': 'Videos'}

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

game_specials = ['platforms', 'genres', 'releases', 'themes', 'images']
# games_times = get_hltb_times()

with open('new_games.txt', 'r') as file:
    lines = file.readlines()


def get_best_match(candidates, title):
    best_match = 0
    best_index = 0
    best_score = 0
    # title = ''.join(ch for ch in title if ch.isalnum() or ch == ' ')
    title = title.replace('&', 'and')
    title_words = [v.translate(str.maketrans('', '', string.punctuation))
                       .lower().strip() for v in re.sub('/|_|-|:', ' ', title).split(' ')]
    # title_words = [v for v in title_words if v != '']
    title_words = [unicodedata.normalize('NFKD', v).encode('ASCII', 'ignore').decode('utf-8')
                   for v in title_words if v != '']
    for ind, candidate in enumerate(candidates):
        # candidate = ''.join(ch for ch in candidate if ch.isalnum() or ch == ' ')
        temp_candidate = candidate.replace('video game', '')
        temp_candidate = temp_candidate.replace('&', 'and')
        candidate_words = [v.translate(str.maketrans('', '', string.punctuation))
                               .lower().strip() for v in re.sub('/|_|-|:', ' ', temp_candidate).split(' ')]
        # candidate_words = [v for v in candidate_words if v != '']
        candidate_words = [unicodedata.normalize('NFKD', v).encode('ASCII', 'ignore').decode('utf-8')
                           for v in candidate_words if v != '']
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


def get_database_connection(host, port, replica_set, username, password):
    if port == '':
        port = '27017'
    port = int(port)
    if replica_set == '':
        replica_set = None

    connection = pymongo.mongo_client.MongoClient(
        host=host,
        port=port,
        replicaSet=replica_set,
        username=username,
        password=password,
        ssl=False
    )
    return connection


connection_games = get_database_connection('localhost', '27017', '', None, None)
giant_games_coll = connection_games['Games']['GiantGames']


def get_steam_url(title):
    try:
        base_url = 'https://store.steampowered.com/search/?term='
        new_title = title.replace(' ', '+')
        url = base_url + new_title

        webpage = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                  'Chrome/50.0.2661.102 Safari/537.36'})
        soup = BeautifulSoup(webpage.text, 'html.parser')
        urls = []
        search_results = soup.findAll('a', {'class':
                                                ['search_result_row ds_collapse_flag', 'app_impression_tracked']})[:10]
        candidates = []
        for result in search_results:
            search_title = result.find('span', {'class': 'title'}).text
            urls.append(result.attrs['href'])
            candidates.append(search_title)

        best_candidate = get_best_match(candidates, title)
        return candidates[best_candidate[0]], best_candidate[1], urls[best_candidate[0]]
    except Exception as _:
        return 'Error', 0, 'Error'


def get_meta_url(title):
    try:
        base_url = 'https://www.metacritic.com/search/'
        new_title = title
        url = base_url + new_title + '/?page=1&category=13'

        webpage = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                                                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                           'Chrome/50.0.2661.102 Safari/537.36'})
        soup = BeautifulSoup(webpage.text, 'html.parser')
        search_results = soup.findAll('a', {'class': 'c-pageSiteSearch-results-item'})[:10]
        candidates = []
        urls = []
        for result in search_results:
            p_elem = result.find('p')
            search_title = p_elem.text.strip()
            search_title = re.sub(' +', ' ', search_title)
            search_title = search_title.replace('\n', '')
            if 'ios' in result.attrs['href'] or 'xbox' in result.attrs['href']:
                continue
            urls.append(base_meta + result.attrs['href'])
            candidates.append(search_title)

        best_candidate = get_best_match(candidates, title)
        return candidates[best_candidate[0]], best_candidate[1], urls[best_candidate[0]]
    except Exception as _:
        return 'Error', 0, 'Error'


def get_wiki_url(title):
    try:
        new_title = title.replace(' ', '+')
        url = 'https://en.wikipedia.org/w/index.php?search=' + new_title + \
                   '+video+game&title=Special:Search&profile=advanced&fulltext=1&ns0=1'

        webpage = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                                                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                           'Chrome/50.0.2661.102 Safari/537.36'})
        soup = BeautifulSoup(webpage.text, 'html.parser')
        search_results = soup.findAll('div', {'class': 'mw-search-result-heading'})[:10]
        candidates = []
        urls = []
        for result in search_results:
            a_elem = result.find('a')
            search_title = a_elem.attrs['title']
            urls.append(a_elem.attrs['href'])
            candidates.append(search_title)

        best_candidate = get_best_match(candidates, title)
        return candidates[best_candidate[0]], best_candidate[1], base_wiki + urls[best_candidate[0]]
    except Exception as _:
        return 'Error', 0, 'Error'


def get_epic_url(title):
    try:
        new_title = title.replace(' ', '+')
        url = 'https://www.epicgames.com/store/en-US/browse?q=' + new_title + '&sortBy=relevancy&sortDir=DESC&count=40'
        webpage = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                                                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                           'Chrome/50.0.2661.102 Safari/537.36'})
        soup = BeautifulSoup(webpage.text, 'html.parser')
        search_results = soup.findAll('div', {'class': 'css-bjn8wh'})[:10]
        candidates = []
        urls = []
        for result in search_results:
            search_title = result.find('span').text
            candidates.append(search_title)
            urls.append(result.find('a').attrs['href'])

        best_candidate = get_best_match(candidates, title)
        return candidates[best_candidate[0]], best_candidate[1], base_epic + urls[best_candidate[0]]
    except Exception as _:
        return 'Error', 0, 'Error'


def get_gameplay_time(title):
    main = '/'
    main_extra = '/'
    complete = '/'
    candidates = []
    indexes = []
    try:
        htlb_games = htlb_obj.search(title, similarity_case_sensitive=False)
        time.sleep(2)
        for ind, game in enumerate(htlb_games):
            if game.similarity > 0.5:
                candidates.append(game.game_name)
                indexes.append(ind)

        best_candidate = htlb_games[get_best_match(candidates, title)[0]]
        main = best_candidate.main_story
        main_extra = best_candidate.main_extra
        complete = best_candidate.completionist
        return [main, main_extra, complete]
    except Exception as e:
        pass
    return [main, main_extra, complete]


def get_gameplay_time_google(title):
    main = '/'
    main_extra = '/'
    complete = '/'
    try:
        results = search(title + ' howlongtobeat', num_results=10, advanced=True)
        links = [hit for hit in results]
        candidates = [v.title.replace('How long is ', '') for v in links if v.url.replace(base_hltb, '').count('/') == 0]
        candidates = [v.replace('?', '') for v in candidates]
        best_candidate = get_best_match(candidates, title)
        best_link = links[best_candidate[0]].url
        webpage = requests.get(best_link, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                                                                 'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                                 'Chrome/50.0.2661.102 Safari/537.36'})
        soup = BeautifulSoup(webpage.text, 'html.parser')
        li_elems = soup.findAll('li', {'class': 'GameStats_short__tSJ6I time_100'})
        times = []
        for li in li_elems:
            times.append(li.find('h5').text.replace('Hours', '').replace('Minutes', '').replace('½', '.5').strip())
    except Exception as _:
        return [main, main_extra, complete]
    return times

'''
def get_game_time(title):
    main = '/'
    main_extra = '/'
    complete = '/'

    try:
        candidates = [v['name'] for v in games_times[title]]
        best_candidate = get_best_match(candidates, title)
        best_candidate = games_times[title][best_candidate[0]]
        # print(best_candidate['name'], title)
        return [best_candidate['main'], best_candidate['main_extra'], best_candidate['complete']]
    except Exception as _:
        return [main, main_extra, complete]
'''

def get_riot_url(title):
    try:
        new_title = title.replace('-', ' ').strip()
        new_title = re.sub(' +', ' ', new_title)
        new_title = new_title.replace(' ', '&')
        url = base_riot + 'search/' + new_title + '/'
        webpage = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                                                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                           'Chrome/50.0.2661.102 Safari/537.36'})
        soup = BeautifulSoup(webpage.text, 'html.parser')
        candidates = json.loads(soup.text)
        candidates_titles = [v['value'] for v in candidates]
        best_candidate = get_best_match(candidates_titles, title)
        return candidates[best_candidate[0]]['value'], best_candidate[1], \
            base_riot + 'games/' + candidates[best_candidate[0]]['id'].replace('games-', '') + '/screenshots/'
    except Exception as _:
        return 'Error', 0, 'Error'


def get_giantbomb_id(title):
    json_obj = {'Name': '', 'Aliases': '', 'GB Intro': '', 'GB Description': '', 'Platforms': '', 'Developers': '',
                'Franchises': '', 'Releases': '', 'Images': '', 'GB Genres': '', 'Themes': '', 'GB Release Date': '',
                'Videos': '', 'Giant Id': ''}
    try:
        response = gb.search(title)
        candidates = [v.name for v in response]
        best_index, best_match, best_score = get_best_match(candidates, title)
        if best_match > 0.7:
            # print(title)
            giant_id = response[best_index].id
            game = gb.get_game(giant_id)
            game_attrs = vars(game)
            game_attrs['title'] = title
            game_attrs['Giant Id'] = giant_id
            game_attrs['image'] = vars(game_attrs['image'])
            for key in game_specials:
                special_obj = game_attrs[key]
                if special_obj is not None:
                    game_attrs[key] = [vars(v) for v in special_obj]
            for k, v in game_attrs.items():
                if k in names_dict:
                    if k == 'platforms' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = [{'Name': obj['name'], 'Abbreviation': obj['abbreviation']} for obj in
                                                   v]
                    elif k == 'developers' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = [obj['name'] for obj in v]
                    elif k == 'publishers' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = [obj['name'] for obj in v]
                    elif k == 'franchises' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = [obj['name'] for obj in v]
                    elif k == 'releases' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = list({obj['name'] for obj in v})
                    elif k == 'images' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = [{'Super': obj['super_url'], 'Screen': obj['screen_url']} for obj in
                                                   v]
                    elif k == 'genres' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = [obj['name'] for obj in v]
                    elif k == 'themes' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = [obj['name'] for obj in v]
                    elif k == 'videos' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = [obj['name'] for obj in v]
                    elif k == 'description' and game_attrs[k] is not None:
                        json_obj[names_dict[k]] = BeautifulSoup(v, 'html.parser').get_text(' ')
                    else:
                        json_obj[names_dict[k]] = v
            for k, v in json_obj.items():
                json_obj[k] = v if v is not None else ''

            # giant_games_coll.insert_one(game_attrs)
        else:
            # print('Match Error', title)
            return json_obj, False
    except Exception as e:
        print('Exception Error', title, e)
        return json_obj, False
    return json_obj, True


try:
    existed_games = []
    for ind, line in enumerate(lines):
        temp_line = line.replace('\n', '')
        gb_name = temp_line
        modification_date = datetime.now()
        modification_date = modification_date.strftime('%d %b, %Y')
        version_date = modification_date
        if ' $ ' in temp_line:
            split_list = temp_line.split(' $ ')
            temp_line = split_list[0]
            gb_name = split_list[1]
        if ' # ' in temp_line:
            split_list = temp_line.split(' # ')
            temp_line = split_list[0]
            version_date = split_list[1]
        # print('Fetching URLs on', temp_line)
        db_obj = giant_games_coll.find_one({'$or': [{'Title': temp_line}, {'Name': gb_name}]})
        if db_obj is not None:
            existed_games.append(temp_line)
            new_values = {'$set': {'Modification Date': modification_date, 'Version Date': version_date}}
            giant_games_coll.update_one({'_id': db_obj['_id']}, new_values)
            continue
        game_dict, found_flag = get_giantbomb_id(temp_line)
        if found_flag:
            db_obj = giant_games_coll.find_one({'Giant Id': game_dict['Giant Id']})
            if db_obj is not None:
                existed_games.append(temp_line)
                continue

        if temp_line == 'Sacred':
            best_steam = get_steam_url(temp_line + ' Gold')
        else:
            best_steam = get_steam_url(temp_line)
        best_wiki = get_wiki_url(temp_line)
        best_meta = get_meta_url(temp_line)
        best_epic = get_epic_url(temp_line)
        best_hltb = get_gameplay_time(temp_line)
        # best_hltb = get_game_time(temp_line)
        best_riot = get_riot_url(temp_line)
        temp_list = [temp_line, best_wiki[0], str(best_wiki[1]), best_wiki[2],
                     best_steam[0], str(best_steam[1]), best_steam[2],
                     best_meta[0], str(best_meta[1]), best_meta[2],
                     best_epic[0], str(best_epic[1]), best_epic[2],
                     best_riot[0], best_riot[1], best_riot[2]]
        temp_list.extend(best_hltb)
        nb_screenshots = 0
        game_title = temp_list[0]

        # print('WIKIPEDIA')
        wiki_score = float(temp_list[2])
        wiki_url = temp_list[3]

        if wiki_score >= 0.75:
            wiki_gameplay_text = '#'
            wiki_plot_text = '#'
            wiki_synopsis_text = '#'
            wiki_genre = '#'
            try:
                webpage = requests.get(wiki_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                                                                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                                   'Chrome/50.0.2661.102 Safari/537.36'})
                soup = BeautifulSoup(webpage.text, 'html.parser')
                wiki_gameplay = soup.find('span', {'id': 'Gameplay'})
                wiki_synopsis = soup.find('span', {'id': 'Synopsis'})
                wiki_plot = soup.find('span', {'id': 'Plot'})
                if wiki_gameplay is not None:
                    wiki_gameplay = wiki_gameplay.parent
                    wiki_gameplay = wiki_gameplay.next_sibling
                    while wiki_gameplay is not None and wiki_gameplay.name != 'h2':
                        if wiki_gameplay.name == 'p':
                            wiki_gameplay_text += wiki_gameplay.text
                        wiki_gameplay = wiki_gameplay.nextSibling
                if wiki_synopsis is not None:
                    wiki_synopsis = wiki_synopsis.parent
                    wiki_synopsis = wiki_synopsis.next_sibling
                    while wiki_synopsis is not None and wiki_synopsis.name != 'h2':
                        if wiki_synopsis.name == 'p':
                            wiki_synopsis_text += wiki_synopsis.text
                        wiki_synopsis = wiki_synopsis.next_sibling
                if wiki_plot is not None:
                    wiki_plot = wiki_plot.parent
                    wiki_plot = wiki_plot.next_sibling
                    while wiki_plot is not None and wiki_plot.name != 'h2':
                        if wiki_plot.name == 'p':
                            wiki_plot_text += wiki_plot.text
                        wiki_plot = wiki_plot.next_sibling

                new_genre_index = [d.text for d in soup.findAll('th', {'class': 'infobox-label'})].index('Genre(s)')
                new_genre = [d.text for d in soup.findAll('td', {'class': 'infobox-data'})][new_genre_index]
                wiki_genre = new_genre.replace(',', ';')
            except Exception as _:
                wiki_genre = '#'
        else:
            wiki_gameplay_text = '#'
            wiki_plot_text = '#'
            wiki_synopsis_text = '#'
            wiki_genre = '#'

        # print('STEAM')
        steam_score = float(temp_list[5])
        steam_url = temp_list[6]

        steam_description = '#'
        steam_summary = '#'
        steam_critics = ''
        steam_nb_users = ''
        steam_genres = ''
        date = ''
        if steam_score >= 0.75:
            try:
                webpage = requests.get(steam_url,
                                       headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                                                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                              'Chrome/50.0.2661.102 Safari/537.36'})
                soup = BeautifulSoup(webpage.text, 'html.parser')
                steam_description = soup.find('div', {'class': 'game_description_snippet'})
                if steam_description is not None:
                    steam_description = steam_description.text
                    steam_description = steam_description.replace('\r', ' ')
                    steam_description = steam_description.replace('\t', ' ')
                    steam_description = steam_description.replace('\n', ' ')
                    steam_description = steam_description.replace("\'", "'")
                    steam_description = steam_description.strip()
                    steam_description = re.sub(' +', ' ', steam_description)
                else:
                    steam_description = '#'

                steam_summary = soup.find('div', {'id': 'aboutThisGame'})
                if steam_summary is not None:
                    steam_summary = steam_summary.text
                    steam_summary = steam_summary.replace('\r', ' ')
                    steam_summary = steam_summary.replace('\t', ' ')
                    steam_summary = steam_summary.replace('\n', ' ')
                    steam_summary = steam_summary.replace("\'", "'")
                    steam_summary = steam_summary.strip()
                    steam_summary = re.sub(' +', ' ', steam_summary)
                else:
                    steam_summary = '#'

                mydivs = soup.findAll('div', {'class': 'user_reviews_summary_row'})
                if len(mydivs) > 2:
                    wanted_div = mydivs[1]

                else:
                    wanted_div = mydivs[0]
                steam_critics = wanted_div.attrs['data-tooltip-html'].split('%')[0]
                steam_nb_users = int(wanted_div.find('span', {'class': 'responsive_hidden'})
                                     .text[1:-1].strip()[1:-1].replace(',', ''))
                date = soup.find('div', {'class': 'date'}).text

                steam_genres = [d.text.replace('\t', '').replace('\r', '').replace('\n', '')
                          for d in soup.findAll('a', {'class': 'app_tag'})]
                steam_genres = ', '.join(steam_genres)

                if download_images:
                    screenshot_divs = soup.findAll('div', {'class': 'screenshot_holder'})
                    for sc_ind, sc_shot_div in enumerate(screenshot_divs[:5]):
                        try:
                            folder = temp_list[0][0].upper()
                            if folder not in alphabet:
                                folder = '#'
                            image_src = sc_shot_div.find('a').attrs['href']
                            response = requests.get(image_src)
                            with open(folder + '/' + temp_list[0] + '_' + str(sc_ind + 1) + '.jpg', 'wb') as img_file:
                                img_file.write(response.content)
                                nb_screenshots += 1
                        except Exception as e:
                            continue

            except Exception as _:
                steam_description = '#'
                steam_summary = '#'

        # print('METACRITIC')
        meta_score = float(temp_list[8])
        meta_url = temp_list[9]

        if meta_score >= 0.75:
            try:
                critics = ''
                users = ''
                webpage = requests.get(meta_url,
                                       headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) '
                                                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                              'Chrome/50.0.2661.102 Safari/537.36'})
                soup = BeautifulSoup(webpage.text, 'html.parser')
                meta_description = soup.find('meta', {'name': 'description'}).attrs['content']
                score_div = soup.find('div', {'class': 'c-reviewsSection'})
                try:
                    critics = score_div.find('div', {'class': 'c-siteReviewScore_background-critic_large'}).find('span').text
                except Exception as e:
                    critics = ''
                try:
                    users = score_div.find('div', {'class': 'c-siteReviewScore_background-user'}).find('span').text
                except Exception as e:
                    users = ''

                if date == '':
                    try:
                        date = soup.find('div', {'class': 'c-gameDetails_ReleaseDate'}).find('span', {'class': 'g-color-gray70'}).text
                    except Exception as _:
                        date = ''
            except Exception as _:
                meta_description = '#'
                critics = ''
                users = ''
        else:
            meta_description = '#'
            critics = ''
            users = ''


        game_dict['Title'] = game_title
        game_dict['Steam Description'] = steam_description
        game_dict['Steam Summary'] = steam_summary
        game_dict['Wikipedia Gameplay'] = wiki_gameplay_text
        game_dict['Wikipedia Plot'] = wiki_plot_text
        game_dict['Wiki Synopsis'] = wiki_synopsis_text
        game_dict['Metacritic Description'] = meta_description
        # game_dict['Metacritic Genre'] = genre
        game_dict['Critics'] = critics
        game_dict['Users'] = users
        game_dict['Steam Users'] = steam_critics
        game_dict['Steam Nb Users'] = steam_nb_users
        # game_dict['Average'] = ((critics / 10) + ((users + steam_critics / 10) / 2)) / 2
        # game_dict['Steam Genre'] = steam_genres
        game_dict['Genres'] = steam_genres
        game_dict['Release Date'] = date

        if nb_screenshots <= 0:
            for item in game_dict['Images']:
                response = requests.get(item['Super'])
                if response.status_code != 200:
                    continue
                folder = temp_list[0][0].upper()
                with open(folder + '/' + temp_list[0] + '_' + str(nb_screenshots + 1) + '.jpg', 'wb') as img_file:
                    img_file.write(response.content)
                    nb_screenshots += 1
                    if nb_screenshots > 5:
                        break
        game_dict['Pictures'] = 'X'
        if nb_screenshots > 0:
            game_dict['Pictures'] = '√'

        # print('HOW LONG TO BEAT')
        game_dict['On List'] = '?'
        game_dict['Story'] = ''
        game_dict['Gameplay'] = ''
        game_dict['Graphics'] = ''
        game_dict['Diversity'] = ''
        game_dict['Music and OST'] = ''
        game_dict['Score'] = ''
        game_dict['Done'] = ''
        game_dict['Main'] = '/'
        game_dict['Main+'] = '/'
        game_dict['Complete'] = '/'
        if str(temp_list[-3]).replace('.', '1').isnumeric():
            game_dict['Main'] = temp_list[-3]
        if str(temp_list[-2]).replace('.', '1').isnumeric():
            game_dict['Main+'] = temp_list[-2]
        if str(temp_list[-1]).replace('.', '1').isnumeric():
            game_dict['Complete'] = temp_list[-1]
        today = datetime.today()
        modification_date = '/'.join([str(today.day), str(today.month), str(today.year)])
        new_date = datetime.strptime(modification_date, '%d/%m/%Y')
        modification_date = new_date.strftime('%d %b, %Y')
        game_dict['Modification Date'] = modification_date
        game_dict['Version Date'] = version_date

        aliases = ''
        if 'Aliases' in game_dict:
            aliases = game_dict['Aliases'].replace('\n', ', ')
        platforms = ''
        if 'Platforms' in game_dict and len(game_dict['Platforms']) > 0:
            platforms = game_dict['Platforms'][0]['Abbreviation']

        giant_id = game_dict['Giant Id'] if 'Giant Id' in game_dict else 0

        print('#'.join([game_dict['Title'], aliases, game_dict['Release Date'], game_dict['Critics'],
                        game_dict['Users'], str(game_dict['Steam Users']), str(game_dict['Steam Nb Users']),
                        str(game_dict['Main']), str(game_dict['Main+']), str(game_dict['Complete']),
                        game_dict['Name']]))
        json_list.append(game_dict)
        giant_games_coll.insert_one(game_dict)
        time.sleep(25)

    print()
    print('################# Games that already exist: ##############################')
    print('\n'.join(existed_games))
    print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
    # print(json_list)

except Exception as e:
    print(e)
