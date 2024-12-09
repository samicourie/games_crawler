import asyncio
import rawg

rawg_key = '8a120bfae1b04e538ad87617801a5e2a'


async def requests(game_list):
    async with rawg.ApiClient(rawg.Configuration(api_key={'key': rawg_key})) as api_client:
        # Create an instance of the API class
        api = rawg.GamesApi(api_client)

        # Making requests
        coros = [api.games_read(id=name) for name in [game_list]]

        # Waiting for requests
        for coro in asyncio.as_completed(coros):
            game: rawg.GameSingle = await coro
            print('——————————————————————————————————————————————')
            print('            Id |', game.id)
            print('   Description |', game.description)
            print('          Name |', game.name)
            print('      Released |', game.released)
            print('        Rating |', game.rating)
            print('  Achievements |', game.achievements_count)
            print('       Website |', game.website)
            print('    Metacritic |', game.metacritic)
            print('Metacritic URL |', game.metacritic_url)
            print('——————————————————————————————————————————————')
            print()

        return game.description

def rawg_description():
    rawg_obj = asyncio.get_event_loop().run_until_complete(requests('mario-luigi'))
    return rawg_obj


if __name__ == '__main__':
    print(rawg_description())
