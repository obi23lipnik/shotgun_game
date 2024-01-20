import random

from constants import b_items, items_list

def get_random_item():
    item_index = random.randint(1, len(items_list.items()))
    return item_index

def get_hp_display(player):
    return ' '.join('❤️' for _ in range(player.hp)) + ''.join(' 🖤' for _ in range(player.max_hp - player.hp))

def get_inventory_display(player):
    return ''.join('[  {}  ]'.format(b_item) for b_item in player.get_beautiful_inv())

class Player:
    name = None
    hp = None
    max_hp = None
    dead = False
    handcuffed = False
    handcuffed_this_round = False
    inventory = []
    aiop = None
    stats_message = None

    def __init__(self, name=None, hp=None, inventory=None, aiop=None):
        if hp:
            self.hp = hp
        else: 
            self.hp = random.randint(2,4)

        if inventory:
            self.inventory = inventory
        else:
            self.inventory = []
        self.name = name
        self.max_hp = self.hp
        self.aiop = aiop
 
    def get_beautiful_inv(self):
        return [b_items[item_number] for item_number in self.inventory]

    def get_stats(self):
        return {
            'name': self.name,
            'hp': self.hp,
            'inventory': self.inventory
        }

    def die(self):
        self.dead = True

    def change_hp(self, diff):
        if self.dead:
            return
        if self.hp + diff > self.max_hp: return
        self.hp += diff
        if self.hp <= 0:
            self.die()

    def add_item_to_inventory(self):
        if len(self.inventory) < 8:
            item_index = get_random_item()
            self.inventory.append(item_index)