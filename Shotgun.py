import random

from constants import b_slugs
from Player import get_hp_display


def cause_effect(itemNumber, shotgun):
    match itemNumber:
        case 1:  # cigarrette
            shotgun.current_holder.change_hp(1)
            return True, shotgun.current_holder.name + ' healed for 1 by smoking🚬, current health: ' + get_hp_display(shotgun.current_holder)
        case 2:  # axe
            if shotgun.dmg == 1:
                shotgun.increase_dmg()
                return True, shotgun.current_holder.name + ' grabs his axe🪓 and sharpens the end of the shotgun. +1dmg'
            else:
                return False, None
        case 3:  # beer
            return True, shotgun.current_holder.name + ' empties the chamber after downing a beer🍺, the slug was: ' + (b_slugs[0] if not shotgun.unload_slug() else b_slugs[1])
        case 4:  # lens
            if shotgun.aiop:
                shotgun.aiop.knows_next = True
            return True, shotgun.current_holder.name + ' checks the chamber with a lens🔎, the next slug is: ' + (b_slugs[0] if not shotgun.slugs[0] else b_slugs[1])
        case 5:  # cuffs
            if not shotgun.current_opponent.handcuffed_this_round and not shotgun.current_opponent.handcuffed:
                shotgun.current_opponent.handcuffed = True
                return True, shotgun.current_holder.name + ' chains🔗 ' + shotgun.current_opponent.name + ' to the ground, preventing their next turn.'
            return False, None
        case 6:
            temp_bullets = shotgun.slugs[:]
            new_bullets = [temp_bullets[0]] + [1] + temp_bullets[1:]
            shotgun.slugs = new_bullets
            if shotgun.aiop:
                shotgun.aiop.knows_second = True
            return True, shotgun.current_holder.name + ' puts an extra live slug🟥 after the next one.'
        case _:
            return False, None

def get_random_slugs(maxSlugs=8):
    live_slugs = random.randint(1, int(maxSlugs/2))
    fake_slugs = live_slugs + 1 if random.random() > 0.5 else live_slugs
    if fake_slugs >= 3 and random.random() > 0.5:
        fake_slugs -= 1
    slugs = [1,] * live_slugs + [0,] * fake_slugs
    random.shuffle(slugs)
    return slugs[:8]

def beautify_slugs(slugs):
    return '  '.join(b_slugs.get(slug) for slug in slugs)

class Shotgun:
    current_holder = None
    current_opponent = None
    handcuffed_this_round = False
    dmg = 1
    slugs = []
    aiop = None

    def __init__(self, player1, player2, holder=None, opponent=None):
        players = [player1, player2]
        random.shuffle(players)
        if not holder:
            self.current_holder = players[0]
        else:
            self.current_holder = holder

        if not opponent:
            self.current_opponent = players[1]
        else:
            self.current_opponent = opponent

    def increase_dmg(self):
        self.dmg = 2

    def load_slugs(self, slugs=get_random_slugs()):
        random.shuffle(slugs)
        self.slugs = slugs
        if self.aiop:
            self.aiop.load_data()
    
    def unload_slug(self):
        slug = self.slugs[0]
        if len(self.slugs) == 1:
            self.slugs = []
        else:
            self.slugs = self.slugs[1:]
        if self.aiop:
            self.aiop.cycle_bullet()
            self.aiop.load_data()
        return slug
    
    def switch_holder(self):
        if self.current_opponent.handcuffed:
            self.current_opponent.handcuffed = False
            self.current_opponent.handcuffed_this_round = True
            return
        self.current_opponent.handcuffed_this_round = False
        temp_opponent = self.current_holder
        self.current_holder = self.current_opponent
        self.current_opponent = temp_opponent

    def shoot_self(self):
        self.current_holder.is_last_shot_self = True
        used_slug = self.slugs[0]
        if used_slug:  # Slug was live
            self.current_holder.change_hp(-self.dmg)
            self.switch_holder()
        self.unload_slug()
        self.dmg = 1
        return used_slug

    def shoot_opponent(self):
        self.current_holder.is_last_shot_self = False
        used_slug = self.slugs[0]
        if used_slug:  # Slug was live
            self.current_opponent.change_hp(-self.dmg)
        self.unload_slug()
        self.dmg = 1
        self.switch_holder()
        return used_slug
