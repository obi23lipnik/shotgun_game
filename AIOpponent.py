import random

from Shotgun import cause_effect

class AiOp:
    player_obj = None
    opponent_obj = None
    shotgun = None
    live_slugs = 0
    blank_slugs = 0
    live_percentage = 0.0
    knows_next = False
    knows_second = False

    def __init__(self, player_obj, opponent_obj, shotgun):
        self.shotgun = shotgun
        self.player_obj = player_obj
        self.opponent_obj = opponent_obj

    def load_data(self):
        slugs = self.shotgun.slugs
        self.live_slugs = slugs.count(1)
        self.blank_slugs = slugs.count(0)
        self.live_percentage = self.live_slugs / len(slugs) if self.live_slugs else 0.0

    def cycle_bullet(self):
        self.knows_next = self.knows_second
        self.knows_second = False

    def use_item(self):
        items = self.player_obj.inventory
        if 1 in items:
            if self.player_obj.hp < self.player_obj.max_hp:
                cause_effect(1, self.shotgun)
                self.player_obj.inventory.pop(items.index(1))
                return True, 1, None
        if 5 in items:
            if not (self.opponent_obj.handcuffed or self.opponent_obj.handcuffed_this_round):
                cause_effect(5, self.shotgun)
                self.player_obj.inventory.pop(items.index(5))
                return True, 5, None
        if 6 in items:
            if self.knows_next and self.shotgun.slugs[0] == 0 and not self.knows_second:
                cause_effect(6, self.shotgun)
                self.player_obj.inventory.pop(items.index(6))
                return True, 6, None
        if 4 in items:
            if not (self.knows_next or (self.live_percentage == 1.0 or self.live_percentage == 0.0)):
                _, effect = cause_effect(4, self.shotgun)
                self.player_obj.inventory.pop(items.index(4))
                return True, 4, effect
        if 3 in items:
            if self.live_slugs + self.blank_slugs >= 2:
                if 0.33 < self.live_percentage < 0.67:
                    _, effect = cause_effect(3, self.shotgun)
                    self.player_obj.inventory.pop(items.index(3))
                    return True, 3, effect
            elif self.live_slugs + self.blank_slugs == 2:
                if self.live_percentage == 1.0:
                    _, effect = cause_effect(3, self.shotgun)
                    self.player_obj.inventory.pop(items.index(3))
                    return True, 3, effect
            if self.live_slugs + self.blank_slugs != 1:
                if self.knows_second and self.shotgun.slugs[1] == 1:
                    _, effect = cause_effect(3, self.shotgun)
                    self.player_obj.inventory.pop(items.index(3))
                    return True, 3, effect
        if 2 in items and not self.shotgun.dmg == 2:
            if self.knows_next:
                if self.shotgun.slugs[0] == 1:
                    cause_effect(2, self.shotgun)
                    self.player_obj.inventory.pop(items.index(2))
                    return True, 2, None
            elif self.live_percentage > 0.67:
                cause_effect(2, self.shotgun)
                self.player_obj.inventory.pop(items.index(2))
                return True, 2, None
        return False, None, None

    def should_shoot_self(self):
        if self.knows_next:
            if self.shotgun.slugs[0] == 1:
                return False
            else:
                return True
        if self.live_slugs > self.blank_slugs:
            return False
        if self.live_slugs == self.blank_slugs:
            return random.random() >= 0.55
        return True