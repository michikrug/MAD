import json
import logging

log = logging.getLogger(__name__)


def generate_quest(quest):
    pokestop_id = quest['pokestop_id']
    quest_reward_text = ''
    quest_reward_type = questreward(quest['quest_reward_type'])
    quest_reward_type_raw = quest['quest_reward_type']
    quest_type = questtype(quest['quest_type'])
    quest_type_raw = quest['quest_type']
    quest_condition = quest['quest_condition']
    quest_target = quest['quest_target']
    quest_template = quest['quest_template']
    name = quest['name']
    latitude = quest['latitude']
    longitude = quest['longitude']
    url = quest['image']
    timestamp = quest['quest_timestamp']

    if quest_reward_type == 'Item':
        item_amount = str(quest['quest_item_amount'])
        item_id = quest['quest_item_id']
        item_type = str(rewarditem(quest['quest_item_id']))
        pokemon_id = "0"
        pokemon_name = ""
        if '{0}' in quest_type:
            quest_type_text = quest_type.replace(
                '{0}', str(quest_target))
        quest_reward_text = item_amount + 'x ' + item_type

    elif quest_reward_type == 'Stardust':
        item_amount = str(quest['quest_stardust'])
        item_type = "Stardust"
        item_id = "000"
        pokemon_id = "0"
        pokemon_name = ""
        if '{0}' in quest_type:
            quest_type_text = quest_type.replace(
                '{0}', str(quest_target))
        quest_reward_text = item_amount + ' ' + item_type

    elif quest_reward_type == 'Pokemon':
        item_amount = "1"
        item_type = "Pokemon"
        item_id = "000"
        pokemon_name = pokemonname(str(quest['quest_pokemon_id']))
        pokemon_id = str(quest['quest_pokemon_id'])
        if '{0}' in quest_type:
            quest_type_text = quest_type.replace(
                '{0}', str(quest_target))
        quest_reward_text = pokemon_name

    quest_raw = ({'pokestop_id': pokestop_id, 'name': name, 'url': url, 'latitude': latitude, 'longitude': longitude,
                  'quest_reward_text': quest_reward_text, 'quest_type_raw': quest_type_raw, 'quest_type': quest_type_text,
                  'quest_condition': quest_condition, 'quest_target': quest_target, 'quest_template': quest_template,
                  'item_amount': item_amount, 'item_type': item_type, 'timestamp': timestamp, 'pokemon_id': pokemon_id,
                  'item_id': item_id, 'pokemon_name': pokemon_name, 'quest_reward_type': quest_reward_type,
                  'quest_reward_type_raw': quest_reward_type_raw})

    return quest_raw


def questreward(quest_reward_type):
    type = {
        2: "Item",
        3: "Stardust",
        7: "Pokemon"
    }
    return type.get(quest_reward_type, "nothing")


def questtype(quest_type):
    with open('utils/quest/types.json') as f:
        items = json.load(f)
    return (items[str(quest_type)]['text'])


def rewarditem(itemid):
    with open('utils/quest/items.json') as f:
        items = json.load(f)
    return (items[str(itemid)]['name'])


def pokemonname(id):
    with open('pokemon.json') as f:
        mondata = json.load(f)
    return mondata[str(int(id))]["name"]
