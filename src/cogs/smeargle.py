import io
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import discord
from PIL import Image
from PIL.Image import Resampling
from discord import MessageType, Message
from discord.ext.commands import Cog, Bot


class Smeargle(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.battleImageCreator = BattleImageCreator()
        self.load_env_vars()

    def load_env_vars(self):
        pass  # TODO: Move a some constants to the env file and load them here

    @Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if message.type != MessageType.reply or not self.bot.user.mentioned_in(message):
            return

        if message.reference is None or message.reference.resolved is None:
            return

        attachments = message.reference.resolved.attachments
        areas = message.content.split(" ")

        for attachment in attachments:
            filename = attachment.filename

            image = Image.open(io.BytesIO(await attachment.read()))

            battle_image = self.battleImageCreator.generate_battle_image(filename, image, areas)

            if battle_image is None:
                await self._send_invalid_id(image, attachment.filename, message)
            else:
                await self._send_battle_image(battle_image, attachment.filename, message)

    @staticmethod
    async def _send_battle_image(image: Image, filename: str, message: Message):
        buffer = io.BytesIO()
        image.save(buffer, "png")
        buffer.seek(0)

        file = discord.File(buffer, filename=filename)

        embed = discord.Embed()
        embed.set_image(url=f"attachment://{filename}")

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
        # self.spriteShadows = self._generate_sprite_shadows() # TODO: Uncommenting until downstream works

    def generate_battle_image(
            self, filename: str, image: Image, areas: Iterable[str]
    ) -> Image:
        image = image.convert("RGBA")

        # TODO: Add regex for single ID (so that custom bases work)
        regex_result = re.search(r"\d+\.(\d+)", filename)
        if regex_result is None:
            return

        body_id = regex_result.group(1)
        area = self._get_area(areas)
        battle = self.battles[area]

        # TODO: Add shadows for player/enemy sprites
        self._add_player_sprite(
            battle, image, self.spriteOffsets[body_id]
        )
        self._add_enemy_sprite(battle, image, self.spriteOffsets[body_id])

        self._add_enemy_dropshadow(battle, image, self.spriteShadows[body_id])

        battle = battle.image.resize(
            (battle.image.width * 3, battle.image.height * 3),
            resample=Resampling.NEAREST,
        )

        return battle

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
                int(battler_shadow_x),
                int(battler_shadow_size),
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

        # TODO: Look into transparency issue:
        #  https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.paste
        background.paste(player_base, player_base_position, player_base)
        background.paste(enemy_base, enemy_base_position, enemy_base)

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

        # TODO: Look into transparency issue:
        #  https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.paste
        battle.image.paste(sprite, position, sprite)

    def _add_enemy_sprite(
            self, battle: Battle, enemy_sprite: Image, sprite_offset: SpriteOffset, sprite_shadow: SpriteShadow
    ) -> None:
        sprite = self.transform_enemy_sprite(enemy_sprite)

        enemy_bottom_centre_position = self.get_enemy_bottom_centre_position(
            battle.image
        )

        position = (
            round(enemy_bottom_centre_position[0] - (sprite.width / 2)) + sprite_offset.enemy_offset[0] + 2,
            round(enemy_bottom_centre_position[1] - (sprite.height / 2))
            + 4
            + sprite_offset.enemy_offset[1]
            - (sprite_offset.altitude * 3),
        )

        # TODO: Look into transparency issue:
        #  https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.paste
        battle.image.paste(sprite, position, sprite)

        shadow_position = self.get_shadow_position()


        battle.image.paste(sprite, position, sprite)

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
        return sprite.resize((96 * 2, 96 * 2), Resampling.NEAREST)

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
