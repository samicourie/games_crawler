from bs4 import BeautifulSoup
from giantbomb import giantbomb
from crawlers.crawler import Crawler

from util.utility import get_best_match


class GiantbombCrawler(Crawler):

    def __init__(self):
        super().__init__()
        self.giantbomb_key = 'f0673d2f0d082808075c28853ecf492fe82f67a2'
        self.gb = giantbomb.Api(self.giantbomb_key, 'API test')
        self.names_dict = {'Giant Id': 'giantbomb-id', 'name': 'giantbomb-name', 'aliases': 'giantbomb-aliases', 'deck': 'giantbomb-intro',
                           'description': 'giantbomb-description', 'platforms': 'giantbomb-platforms', 'developers': 'giantbomb-developers',
                           'publishers': 'giantbomb-publishers', 'franchises': 'giantbomb-franchises', 'releases': 'giantbomb-releases', 
                           'images': 'giantbomb-screenshots', 'genres': 'giantbomb-genres', 'themes': 'giantbomb-themes', 
                           'original_release_date': 'giantbomb-release-date', 'similar_games': 'giantbomb-similar-games'}
        self.game_specials = ['platforms', 'genres', 'releases', 'themes', 'images']

    def get_api_info(self, title):
        json_obj = {}
        success = False
        try:
            response = self.gb.search(title)
            candidates = [v.name for v in response]
            best_index, best_score, _ = get_best_match(candidates, title)
            if best_score >= self.accepted_score:
                giant_id = response[best_index].id
                game = self.gb.get_game(giant_id)
                game_attrs = vars(game)
                game_attrs['title'] = title
                game_attrs['Giant Id'] = giant_id
                game_attrs['image'] = vars(game_attrs['image'])
                for key in self.game_specials:
                    special_obj = game_attrs[key]
                    if special_obj is not None:
                        game_attrs[key] = [vars(v) for v in special_obj]

                for k, v in game_attrs.items():
                    if k in self.names_dict:
                        if k in ['platforms', 'developers', 'publishers', 'franchises', 'releases', 'themes', 'genres'] and game_attrs[k] is not None:
                            json_obj[self.names_dict[k]] = '; '.join([obj['name'] for obj in v])
                        elif k == 'images' and game_attrs[k] is not None:
                            json_obj[self.names_dict[k]] = [obj['super_url'].replace('scale_large', 'original') for obj in v]
                        elif k == 'similar_games' and game_attrs[k] is not None:
                            json_obj[self.names_dict[k]] = [{obj['name']: obj['id']} for obj in v]
                            json_obj['giantbomb-similar-titles'] = '; '.join([obj['name'] for obj in v])
                        elif k == 'description' and game_attrs[k] is not None:
                            json_obj[self.names_dict[k]] = BeautifulSoup(v, 'html.parser').get_text(' ')
                        else:
                            json_obj[self.names_dict[k]] = v
                for k, v in json_obj.items():
                    json_obj[k] = v if v is not None else ''
                json_obj['giantbomb-score'] = best_score
                success = True

        except Exception as _:
            pass
        json_obj['giantbomb-success'] = success
        return json_obj

    def get_url(self, title):
        return super().get_url(title)
    
    def get_info(self, url, score):
        return super().get_info(url, score)
