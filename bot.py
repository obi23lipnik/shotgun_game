import asyncio
import random

import interactions
from discord_token import TOKEN
from AIOpponent import AiOp
from Player import Player, get_hp_display, get_inventory_display
from Shotgun import Shotgun, beautify_slugs, cause_effect, get_random_slugs
from constants import b_nums, nums_b, cool_win_messages, items_list, items_description, neutral_win_messages, cool_suicide_messages


intents = interactions.Intents.DEFAULT
intents.message_content = True
intents.moderation = True
game_channels = []
skip_tutorial_users = []
skip_tutorial_users_file = open('skip_tutorial.txt', 'r')
for user_mention in skip_tutorial_users_file.readlines():
    skip_tutorial_users.append(user_mention)

async def remember_skip_tutorial_user(user_mention):
    skip_tutorial_users_file_w = open('skip_tutorial.txt', 'a')
    skip_tutorial_users_file_w.write(user_mention)

async def forget_skip_tutorial_user(user_mention):
    skip_tutorial_users_file = open('skip_tutorial.txt', 'r')
    skip_tutorial_users_file_w = open('skip_tutorial.txt', 'w')
    for line in skip_tutorial_users_file.readlines():
        if line != user_mention: 
            skip_tutorial_users_file_w.write(line)

def get_everyone_role(server_roles):
    for role in server_roles:
        if role.name == '@everyone':
            return role

def get_player_stats(player, shotgun):
    return (
        player.name +
        '{}{}'.format(
            '🔗' if player.handcuffed else '',
            '🔫{}'.format('🪓' if shotgun.dmg == 2 else '  ') if player == shotgun.current_holder else '',
        ) +
        '\n' +
        '{}'.format(get_hp_display(player)) +
        '\n{}'.format(''.join(
            '[  {}  ]'.format(b_item) for b_item in player.get_beautiful_inv()))
    )

def add_reaction_async(message, emoji):
    loop = asyncio.get_event_loop()
    loop.create_task(message.add_reaction(emoji))

def get_instructions(shotgun, full=True):
    if full:
        return (
            'Turn: ' + shotgun.current_holder.name + '\n'
            'Click a reaction under your item to use it.\n' +
            ''.join('{}: {}\n'.format(items_list[i], items_description[i]) for i in range(1, len(items_list) + 1)) +
            'Click a reaction below to take your action\n'
            '🔼 - Shoot opponent\n'
            '🔽 - Shoot yourself (skip opponent if blank)\n'
            '⏭️ - Remove instructions'
        )
    else:
        return 'Turn: ' + shotgun.current_holder.name

class GameChannel:
    channel_id = None
    mention = None
    occupied = False

    def __init__(self, channel_id, mention):
        self.channel_id = channel_id
        self.mention = mention

    async def init_game_channel(self):
        self.occupied = False
        channel = None
        channel = client.get_channel(self.channel_id)
        everyone_role = get_everyone_role(channel.guild.roles)
        await channel.set_permission(
            everyone_role,
            send_messages=False,
            add_reactions=False,
            read_message_history=True,
            view_channel=True
        )
        await channel.set_permission(client.user, send_messages=True, add_reactions=True)
        await channel.purge()

    async def setup_game_channel(self, player1: interactions.User):
        def check(reaction, user):
            return (
                reaction.message.channel.id == self.channel_id and 
                user != client.user
            )
        channel = client.get_channel(self.channel_id)
        stop_inner_loop = False
        stop_outer_loop = False
        while(not stop_outer_loop and channel):
            await channel.purge()
            await channel.send('Player: ' + player1.mention + ' is waiting to play...')
            message = await channel.send('Do you want to play a game of shotgun with ' + player1.display_name + '? ('+ player1.display_name +' can press 👤 to play with AI or ❌ to cancel lobby)', silent=True)
            add_reaction_async(message, '<:voted:1197236357249114233>')
            add_reaction_async(message, '👤')
            add_reaction_async(message, '❌')

            while (not stop_inner_loop):
                try:
                    reaction, player2 = await client.wait_for('reaction_add', checks=check, timeout=600)
                except asyncio.TimeoutError:
                    await channel.purge()
                    stop_inner_loop = True
                    stop_outer_loop = True
                    await self.init_game_channel()
                    continue

                if str(reaction.emoji) == '❌' and player1 == player2:
                    await channel.purge()
                    stop_inner_loop = True
                    stop_outer_loop = True
                    await self.init_game_channel()
                    continue
                if str(reaction.emoji) == '<:voted:1197236357249114233>':
                    if player2.id == client.user.id:
                        continue
                    elif player1 == player2:
                        await channel.send(
                            'Sorry ' + player1.mention + ', you can\'t play by yourself..',
                            delete_after=3,
                            silent=True,
                        )
                        continue
                    else:
                        stop_inner_loop = True
                        stop_outer_loop = True
                        await self.start_game(channel, player1, player2=player2)
                if str(reaction.emoji) == '👤' and player1 == player2:
                        stop_inner_loop = True
                        stop_outer_loop = True
                        await self.start_game(channel, player1, play_ai=True)


    async def start_game(self, channel, player1, player2=None, play_ai=False):
        def check(reaction, user):
            return (
                reaction.message.channel.id == self.channel_id and 
                user != client.user and
                user in (player1, player2)
            )
        s_player1 = None
        s_player2 = None
        shotgun = None
        if play_ai:
            s_player1 = Player(name=player1.mention)
            s_player2 = Player(name='Strange man', hp=s_player1.hp)
            shotgun = Shotgun(s_player1, s_player2)
            self.aiop = AiOp(s_player2, s_player1, shotgun)
            s_player2.aiop = self.aiop
            shotgun.aiop = self.aiop
        else:
            s_player1 = Player(name=player1.mention)
            s_player2 = Player(name=player2.mention, hp=s_player1.hp)
            shotgun = Shotgun(s_player1, s_player2)
        await channel.purge()
        try:
            log_messages = []
            instructions = None
            while(s_player1.hp > 0 and s_player2.hp > 0):
                for _ in range(0, random.randint(1, 3)):
                    s_player1.add_item_to_inventory()
                    s_player2.add_item_to_inventory()
                async with channel.typing():
                    for i in range(0, len(log_messages)):
                        await log_messages[i].delete()
                    log_messages = []
                random_slugs = get_random_slugs()
                
                async with channel.typing():
                    slugs_message = await channel.send('Slugs: ' + beautify_slugs(random_slugs), delete_after=5, silent=True)
                    await asyncio.sleep(4)
                await slugs_message.delete()
                shotgun.load_slugs(random_slugs)

                while(len(shotgun.slugs) != 0 and s_player1.hp > 0 and s_player2.hp > 0):
                    async with channel.typing():
                        for i in range(0, len(log_messages)):
                            await log_messages[i].delete()
                        log_messages = []
                    async with channel.typing():
                        if s_player1.stats_message:
                            await s_player1.stats_message.edit(content=get_player_stats(s_player1, shotgun))
                        else:
                            s_player1.stats_message = await channel.send(get_player_stats(s_player1, shotgun))
                        if s_player2.stats_message:
                            await s_player2.stats_message.edit(content=get_player_stats(s_player2, shotgun))
                        else:
                            s_player2.stats_message = await channel.send(get_player_stats(s_player2, shotgun))
                    if shotgun.current_holder.aiop:
                        if instructions:
                            await instructions.delete()
                            instructions = None
                        while(True):
                            used_item, item, effect = shotgun.current_holder.aiop.use_item()
                            print(used_item, item, effect)
                            if used_item:
                                if item == 5:
                                    await s_player1.stats_message.edit(content=get_player_stats(s_player1, shotgun))
                                if effect:
                                    async with channel.typing():
                                        await s_player2.stats_message.edit(content=get_player_stats(s_player2, shotgun))
                                        log_messages.append(await channel.send(effect, silent=True))
                            else:
                                break
                        shoot_self = shotgun.current_holder.aiop.should_shoot_self()
                        if shoot_self:
                            print('bot shoot self')                                
                            async with channel.typing():
                                log_messages.append(await channel.send(shotgun.current_holder.name + ' aims the barell of the shotgun at himself...', silent=True))
                            async with channel.typing():
                                await asyncio.sleep(3.0 + (3 * random.random()))
                                current_damage = shotgun.dmg
                                current_holder = shotgun.current_holder.name
                                shot_live = shotgun.shoot_self()
                                if shot_live:
                                    log_messages.append(await channel.send('BOOM! ' + current_holder + ' -' + '{}'.format(current_damage) + 'hp', silent=True))
                                else:
                                    log_messages.append(await channel.send('...click', silent=True))
                            await asyncio.sleep(3)
                        else:
                            print('bot shoot you')
                            async with channel.typing():
                                log_messages.append(await channel.send(shotgun.current_holder.name + ' aims the barell of the shotgun at ' + shotgun.current_opponent.name, silent=True))
                            async with channel.typing():
                                await asyncio.sleep(3.0 + (3 * random.random()))
                                current_damage = shotgun.dmg
                                current_opponent = shotgun.current_opponent.name
                                shot_live = shotgun.shoot_opponent()
                                if shot_live:
                                    log_messages.append(await channel.send('BOOM! ' + current_opponent + ' -' + '{}'.format(current_damage) + 'hp', silent=True))
                                else:
                                    log_messages.append(await channel.send('...click', silent=True))
                            await asyncio.sleep(3)
                            
                    else:
                        if instructions:
                            await instructions.delete()
                            instructions = None
                        if shotgun.current_holder.name in skip_tutorial_users:
                            instructions = await channel.send(get_instructions(shotgun, False), silent=True)
                            add_reaction_async(instructions, '🔼')
                            add_reaction_async(instructions, '🔽')
                            add_reaction_async(instructions, 'ℹ️')
                        else:
                            instructions = await channel.send(get_instructions(shotgun, True), silent=True)
                            add_reaction_async(instructions, '🔼')
                            add_reaction_async(instructions, '🔽')
                            add_reaction_async(instructions, '⏭️')
                        b_inventory = shotgun.current_holder.get_beautiful_inv()
                        for i in range(0, len(b_inventory)):
                            add_reaction_async(shotgun.current_holder.stats_message, b_nums[i+1])
                        break_reactions_loop = False
                        while(not break_reactions_loop):
                            reaction, player = await client.wait_for('reaction_add', checks=check, timeout=600)
                            if player.id == client.user.id:
                                continue
                            elif not player.mention == shotgun.current_holder.name:
                                await channel.send('Wait your turn ' + player.mention, delete_after=10, silent=True)
                            else:
                                if reaction.emoji in [kv_pair for kv_pair in b_nums.values()]:
                                    used_item = shotgun.current_holder.inventory[nums_b[reaction.emoji]-1]
                                    success, effect = cause_effect(
                                        used_item,
                                        shotgun
                                    )
                                    if success:
                                        async with channel.typing():
                                            if effect:
                                                log_messages.append(await channel.send(effect, silent=True))
                                        shotgun.current_holder.inventory.pop(nums_b[reaction.emoji]-1)
                                        async with channel.typing():
                                            await shotgun.current_holder.stats_message.clear_reactions()
                                            await shotgun.current_opponent.stats_message.clear_reactions()
                                            if s_player1.stats_message:
                                                await s_player1.stats_message.edit(content=get_player_stats(s_player1, shotgun))
                                            else:
                                                s_player1.stats_message = await channel.send(get_player_stats(s_player1, shotgun))
                                            if s_player2.stats_message:
                                                await s_player2.stats_message.edit(content=get_player_stats(s_player2, shotgun))
                                            else:
                                                s_player2.stats_message = await channel.send(get_player_stats(s_player2, shotgun))
                                            new_inventory = shotgun.current_holder.get_beautiful_inv()
                                            if new_inventory:
                                                for i in range(0, len(new_inventory)):
                                                    add_reaction_async(shotgun.current_holder.stats_message, b_nums[i+1])
                                    else:
                                        async with channel.typing():
                                            await channel.send('Can\'t use that item right now...', delete_after=3, silent=True)
                                else:
                                    match reaction.emoji:
                                        case '🔼':
                                            current_damage = shotgun.dmg
                                            current_holder = shotgun.current_holder.name
                                            current_opponent = shotgun.current_opponent.name
                                            shot_live = shotgun.shoot_opponent()
                                            
                                            async with channel.typing():
                                                log_messages.append(await channel.send(current_holder + ' aims the barell of the shotgun at ' + current_opponent, silent=True))
                                            async with channel.typing():
                                                await asyncio.sleep(3.0 + (3 * random.random()))
                                                if shot_live:
                                                    log_messages.append(await channel.send('BOOM! ' + current_opponent + ' -' + '{}'.format(current_damage) + 'hp', silent=True))
                                                else:
                                                    log_messages.append(await channel.send('...click', silent=True))
                                            await asyncio.sleep(3)
                                            break
                                        case '🔽':
                                            current_damage = shotgun.dmg
                                            current_holder = shotgun.current_holder.name
                                            shot_live = shotgun.shoot_self()
                                            async with channel.typing():
                                                log_messages.append(await channel.send(current_holder + ' aims the barell of the shotgun at themself', silent=True))
                                            async with channel.typing():
                                                await asyncio.sleep(3.0 + (3 * random.random()))
                                                if shot_live:
                                                    log_messages.append(await channel.send('BOOM! ' + current_holder + ' -' + '{}'.format(current_damage) + 'hp', silent=True))
                                                else:
                                                    log_messages.append(await channel.send('...click', silent=True))
                                            await asyncio.sleep(3)
                                            break
                                        case '⏭️':
                                            loop = asyncio.get_event_loop()
                                            loop.create_task(remember_skip_tutorial_user(shotgun.current_holder.name))
                                            skip_tutorial_users.append(shotgun.current_holder.name)
                                            await instructions.delete()
                                            instructions = None
                                            break
                                        case 'ℹ️':
                                            loop = asyncio.get_event_loop()
                                            loop.create_task(forget_skip_tutorial_user(shotgun.current_holder.name))
                                            skip_tutorial_users.pop(skip_tutorial_users.index(shotgun.current_holder.name))
                                            await instructions.delete()
                                            instructions = None
                                            break
                                        case _:
                                            continue
        except asyncio.TimeoutError:
            await channel.purge()
            await self.init_game_channel()
        else:
            winner = s_player1 if s_player1.hp > 0 else s_player2
            loser = s_player1 if s_player1.hp <= 0 else s_player2
            win_messages = neutral_win_messages
            if loser.is_last_shot_self:
                win_messages += cool_suicide_messages
            else:
                win_messages += cool_win_messages
            win_message = random.choice(cool_win_messages)
            await channel.send(win_message.format(winner=winner.name, loser=loser.name), silent=True)
            await asyncio.sleep(15)
            await channel.purge()
            await self.init_game_channel()

@interactions.listen(interactions.api.events.Startup)
async def ready_up(event: interactions.api.events.Startup):
        print(f'Logged on as {event.bot}!')
        server_channels = 0
        open_channels = []
        for guild in client.guilds:
            for channel in guild.channels:
                channel.id
                if channel.name.startswith('shotgun_game'):
                    print(channel.guild.name + '> ' + channel.name)
                    open_channels.append(channel)
                    server_channels += 1
                    if server_channels >= 3:
                        break
        print(open_channels)
        loop = asyncio.get_event_loop()
        for channel in open_channels:
            ch = GameChannel(channel.id, channel.mention)
            game_channels.append(ch)
            loop.create_task(ch.init_game_channel())

@interactions.slash_command(name="shotgun", description="Start a game of shotgun", scopes=[1092824291533410338])
async def shotgun_start_game_command(ctx: interactions.SlashContext):
    for game_channel in game_channels:
        if not game_channel.occupied and game_channel.channel_id in (channel_id for channel_id in ctx.guild.channels):
            game_channel.occupied = True
            loop = asyncio.get_event_loop()
            loop.create_task(game_channel.setup_game_channel(ctx.user))
            client.get_channel(game_channel.channel_id)
            await ctx.send(
                'We have a room waiting for you ' + ctx.user.mention + ': ' + game_channel.mention,
                delete_after=10,
                silent=True
            )
            return
    await ctx.send(
        'No available channels, sorry ' + ctx.user.mention + '! Try again later',
        delete_after=10,
        silent=True
    )

client = interactions.Client(intents=intents)
client.start(TOKEN)
