import io
import os
import random
import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import discord
from PIL import Image
from PIL.Image import Resampling
from discord import Message
from discord.ext.commands import Bot, Cog, Context, command

from cogs.utils import id_to_name_map


class Smeargle(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.battleImageCreator = BattleImageCreator()
        self.load_env_vars()

    def load_env_vars(self):
        pass  # TODO: Move a some constants to the env file and load them here

    @command(name="battle", pass_context=True,
             help ="Generates a battle image for a sprite.",
             brief = "Generates a battle image")
    async def battle(self, ctx: Context, start_args:str = ""):

        replied_post_reference = ctx.message.reference
        if replied_post_reference is None:
            error_message = "Please reply to a message with an image"
            await ctx.send(error_message, ephemeral=True, delete_after=6)
            await ctx.message.delete(delay=2)
            return
        
        msg = await ctx.channel.fetch_message(replied_post_reference.message_id)

        attachments = msg.attachments
        areas = start_args.split(" ")

        for attachment in attachments:
            filename = attachment.filename

            image = Image.open(io.BytesIO(await attachment.read()))

            body_id = self._determine_body_id_from_filename(filename)
            if body_id == 0:
                error_message = "Cannot parse pokemon id from filename. Please make sure filename is in format `###.###.png` for a fusion or `###.png` for a custom base"
                await ctx.send(error_message, ephemeral=True, delete_after=30)
                await ctx.message.delete(delay=2)
                return

            battle_image, area = self.battleImageCreator.generate_battle_image(body_id, image, areas)

            if battle_image is None:
                await self._send_invalid_id(image, attachment.filename, msg)
            else:
                body_mon = id_to_name_map()[body_id]
                await self._send_battle_image(battle_image, attachment.filename, body_mon, area, msg)

    @staticmethod
    async def _send_battle_image(image: Image, filename: str, body_mon: str, area: str, message: Message):
        buffer = io.BytesIO()
        image.save(buffer, "png")
        buffer.seek(0)

        file = discord.File(buffer, filename=filename)

        embed = discord.Embed()
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=f"{body_mon} body fighting in '{area}'")

        await message.channel.send(file=file, embed=embed)

    @staticmethod
    async def _send_invalid_id(image: Image, filename: str, message: Message):
        buffer = io.BytesIO()
        image.save(buffer, "png")
        buffer.seek(0)

        file = discord.File(buffer, filename=filename)

        embed = discord.Embed(title="Invalid filename",
                              description="Filename must be a valid fusion filename. E.g. 293.59.png")
        embed.set_image(url=f"attachment://{filename}")

        await message.channel.send(file=file, embed=embed)
    
    @staticmethod
    def _determine_body_id_from_filename(filename: str) -> str:
        regex_result = re.search(r"\d+\.(\d+)", filename)
        if regex_result is None:
            # This might be a custom base
            regex_result = re.search(r"(\d+)", filename)
            if regex_result is None:
                return 0

        return regex_result.group(1)        


@dataclass
class SpriteOffset:
    player_offset: tuple[int, int]
    enemy_offset: tuple[int, int]
    altitude: int

@dataclass
class SpriteShadow:
    shadow_x: int
    shadow_size: int

@dataclass
class Battle:
    image: Image
    player_base_position: tuple[int, int]
    enemy_base_position: tuple[int, int]


class BattleImageCreator:
    def __init__(self):
        self.basePath = Path(os.path.join(os.getcwd(), "src", "smeargle-data"))
        self.battles = self._generate_battles(self.basePath)
        self.spriteOffsets = self._generate_sprite_offsets()
        self.spriteShadows = self._generate_sprite_shadows()

    def generate_battle_image(
            self, body_id: str, image: Image, areas: Iterable[str]
    ) -> Image:
        image = image.convert("RGBA")

        area = self._get_area(areas)
        battle = copy.deepcopy(self.battles[area])

        self._add_player_sprite(
            battle, image, self.spriteOffsets[body_id]
        )
        self._add_enemy_dropshadow(battle, self.spriteShadows[body_id])

        self._add_enemy_sprite(battle, image, self.spriteOffsets[body_id])

        self._add_health_bars(battle)

        battle = battle.image.resize(
            (battle.image.width * 3, battle.image.height * 3),
            resample=Resampling.NEAREST,
        )
        
        return battle, area

    def _clear_battle(self):
        pass

    def _generate_sprite_offsets(self) -> dict[Any, SpriteOffset]:
        with open(Path(self.basePath, "pokemon.txt")) as file:
            segments = file.read().split("#-------------------------------")

        offsets = {}
        for segment in segments:
            pokemon_id = re.search(r"\[(\d+)]", segment)
            battler_player_x = re.search(r"BattlerPlayerX = (-?\d+)", segment)
            battler_player_y = re.search(r"BattlerPlayerY = (-?\d+)", segment)
            battler_enemy_x = re.search(r"BattlerEnemyX = (-?\d+)", segment)
            battler_enemy_y = re.search(r"BattlerEnemyY = (-?\d+)", segment)
            battler_shadow_x = re.search(r"BattlerShadowX = (-?\d+)", segment)
            battler_shadow_size = re.search(r"BattlerShadowSize = (-?\d+)", segment)
            battler_altitude = re.search(r"BattlerAltitude = (-?\d+)", segment)

            if None in (
                    pokemon_id,
                    battler_player_x,
                    battler_player_y,
                    battler_enemy_x,
                    battler_enemy_y,
                    battler_shadow_x,
                    battler_shadow_size,                    
            ):
                continue

            offsets[pokemon_id.group(1)] = SpriteOffset(
                (int(battler_player_x.group(1)), int(battler_player_y.group(1))),
                (int(battler_enemy_x.group(1)), int(battler_enemy_y.group(1))),
                (
                    0
                    if battler_altitude is None
                    else int(battler_altitude.group(1))
                ),
            )

        return offsets

    def _generate_sprite_shadows(self) -> dict[Any, SpriteShadow]:
        with open(Path(self.basePath, "pokemon.txt")) as file:
            segments = file.read().split("#-------------------------------")

        offsets = {}
        for segment in segments:
            pokemon_id = re.search(r"\[(\d+)]", segment)
            battler_shadow_x = re.search(r"BattlerShadowX = (-?\d+)", segment)
            battler_shadow_size = re.search(r"BattlerShadowSize = (-?\d+)", segment)

            if None in (
                    pokemon_id,
                    battler_shadow_x,
                    battler_shadow_size,                    
            ):
                continue
            
            offsets[pokemon_id.group(1)] = SpriteShadow(
                int(battler_shadow_x.group(1)),
                int(battler_shadow_size.group(1)),
            )

        return offsets


    def _generate_battles(self, base_path: Path | str) -> dict[str, Battle]:
        areas = [
            child for child in Path(base_path, "images").iterdir() if child.is_dir()
        ]

        battles = {}
        for area in areas:
            player_base = Path(area, "player-base.png")
            enemy_base = Path(area, "enemy-base.png")
            background = Path(area, "background.png")

            if any(
                    (
                        not player_base.is_file(),
                        not enemy_base.is_file(),
                        not background.is_file(),
                    )
            ):
                continue

            battles[area.name] = self._generate_battle(
                player_base, enemy_base, background
            )

        return battles

    def _generate_battle(
            self, player_base_path: Path, enemy_base_path: Path, background_path: Path
    ) -> Battle:
        player_base = self.open_image(player_base_path)
        enemy_base = self.open_image(enemy_base_path)
        background = self.open_image(background_path)

        player_bottom_centre_position = self.get_player_bottom_centre_position(
            background
        )
        player_base_position = (
            round(player_bottom_centre_position[0] - (player_base.width / 2)),
            player_bottom_centre_position[1] - player_base.height,
        )

        enemy_bottom_centre_position = self.get_enemy_bottom_centre_position(background)
        enemy_base_position = (
            round(enemy_bottom_centre_position[0] - (enemy_base.width / 2)),
            enemy_bottom_centre_position[1],
        )

        background.alpha_composite(player_base, dest = player_base_position)
        background.alpha_composite(enemy_base, dest = enemy_base_position)

        return Battle(background, player_base_position, enemy_base_position)

    def _add_player_sprite(
            self, battle: Battle, player_sprite: Image, sprite_offset: SpriteOffset
    ) -> None:
        sprite = self.transform_player_sprite(player_sprite)

        player_bottom_centre_position = self.get_player_bottom_centre_position(
            battle.image
        )
        position = (
            round(player_bottom_centre_position[0] - (sprite.width / 2))
            + sprite_offset.player_offset[0]
            - 2,
            round(player_bottom_centre_position[1] - sprite.height) + 20 + sprite_offset.player_offset[1],
        )

        battle.image.alpha_composite(sprite, dest=position)


    def _add_enemy_sprite(
            self, battle: Battle, enemy_sprite: Image, sprite_offset: SpriteOffset
    ) -> None:
        sprite = self.transform_enemy_sprite(enemy_sprite)

        enemy_bottom_centre_position = self.get_enemy_bottom_centre_position(
            battle.image
        )

        position = (
            round(enemy_bottom_centre_position[0] - (sprite.width / 2)) + (sprite_offset.enemy_offset[0]*2) + 2,
            round(enemy_bottom_centre_position[1] - (sprite.height/2)) + (sprite_offset.enemy_offset[1] * 2)
            - 12
            - (sprite_offset.altitude * 2),
        )

        battle.image.alpha_composite(sprite, dest=position)

    def _add_enemy_dropshadow(
            self, battle: Battle, sprite_shadow: SpriteShadow
    ) -> None:
        shadow = self.get_shadow_image(sprite_shadow.shadow_size)

        enemy_bottom_centre_position = self.get_enemy_bottom_centre_position(
            battle.image
        )

        position = (
            round(enemy_bottom_centre_position[0] - (shadow.width / 2) ) - (sprite_shadow.shadow_x),
            (round(enemy_bottom_centre_position[1] - (shadow.height / 2)  + (128/2) ) )
        )

        battle.image.alpha_composite(shadow, dest =position)

    def _add_health_bars(self, battle: Battle) -> None:
        healthbar = self.get_healthbar_image()

        position = (
            round(((battle.image.width) - 244)),
            round(((battle.image.height)  - (176 ))) + round(healthbar.height)
        )
        battle.image.paste(healthbar, position, healthbar)

        foe_healthbar = self.get_foe_healthbar_image()

        # This is the correct position for modified UI
        # foe_position = (
        #     (8 - 18//2),
        #     (0 + 12) + (foe_healthbar.height//2) 
        # )

        foe_position = (
            8,
            0
        )

        battle.image.alpha_composite(foe_healthbar, dest=foe_position)

    def _get_area(self, areas):
        for area in areas:
            if area in self.battles.keys():
                return area

        return random.choice(list(self.battles.keys()))

    @staticmethod
    def transform_player_sprite(sprite: Image.Image) -> Image.Image:
        return sprite.transpose(Image.FLIP_LEFT_RIGHT).resize(
            (96 * 3, 96 * 3), Resampling.NEAREST
        )

    @staticmethod
    def transform_enemy_sprite(sprite: Image.Image) -> Image.Image:
        return sprite.resize((96 * 2, 96 * 2), Resampling.NEAREST)\
        
    @staticmethod
    def get_shadow_image(shadow_size: int) -> Image.Image:
        shadow_path = os.path.join(os.getcwd(), "src", "smeargle-data", "shadows", f"{shadow_size}.png")
        return BattleImageCreator.open_image(shadow_path)

    @staticmethod
    def get_healthbar_image() -> Image.Image:
        healthbar_path = os.path.join(os.getcwd(), "src", "smeargle-data", "overlay", "databox_normal.png")
        return BattleImageCreator.open_image(healthbar_path)
    
    @staticmethod
    def get_foe_healthbar_image() -> Image.Image:
        healthbar_path = os.path.join(os.getcwd(), "src", "smeargle-data", "overlay", "databox_normal_foe.png")
        return BattleImageCreator.open_image(healthbar_path)

    @staticmethod
    def open_image(file_path) -> Image.Image:
        return Image.open(file_path).convert("RGBA")

    @staticmethod
    def get_player_bottom_centre_position(background: Image) -> tuple[int, int]:
        return 128, background.height + 16

    @staticmethod
    def get_enemy_bottom_centre_position(background: Image) -> tuple[int, int]:
        return (
            background.width - 128,
            round((background.height * 3 / 4) - 112 + 8),
        )


async def setup(bot: Bot):
    await bot.add_cog(Smeargle(bot))
