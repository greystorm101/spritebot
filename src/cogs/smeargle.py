import io
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
class Offset:
    player_offset: tuple[int, int]
    enemy_offset: tuple[int, int]


@dataclass
class Battle:
    image: Image
    player_base_position: tuple[int, int]
    enemy_base_position: tuple[int, int]


class BattleImageCreator:
    def __init__(self):
        self.basePath = Path("smeargle-data")
        self.battles = self._generate_battles(self.basePath)
        self.spriteOffsets = self._generate_sprite_offsets()

    def _generate_sprite_offsets(self) -> dict[Any, Offset]:
        with open(Path(self.basePath, "pokemon.txt")) as file:
            data = file.read()

        ids = re.findall(r"\[(\d+)]", data)

        player_offsets = list(
            zip(
                tuple(
                    [int(el) for el in re.findall(r"BattlerPlayerX = (-?\d+)", data)]
                ),
                tuple(
                    [int(el) for el in re.findall(r"BattlerPlayerY = (-?\d+)", data)]
                ),
            )
        )

        enemy_offsets = list(
            zip(
                tuple([int(el) for el in re.findall(r"BattlerEnemyX = (-?\d+)", data)]),
                tuple([int(el) for el in re.findall(r"BattlerEnemyY = (-?\d+)", data)]),
            )
        )

        offsets = {}
        for ind, el in enumerate(ids):
            offsets[el] = Offset(player_offsets[ind], enemy_offsets[ind])

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

    def _generate_battle(self, player_base_path: Path, enemy_base_path: Path, background_path: Path) -> Battle:
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

        background.paste(player_base, player_base_position, player_base)
        background.paste(enemy_base, enemy_base_position, enemy_base)

        return Battle(background, player_base_position, enemy_base_position)

    def add_player_sprite(self, battle: Battle, player_sprite: Image, offset: tuple[int, int]) -> None:
        sprite = self.transform_player_sprite(player_sprite)

        player_bottom_centre_position = self.get_player_bottom_centre_position(battle.image)
        position = (
            round(player_bottom_centre_position[0] - (sprite.width / 2)) + offset[0] - 2,
            round(player_bottom_centre_position[1] - sprite.height) + 20 + offset[1]
        )

        battle.image.paste(sprite, position, sprite)

    def add_enemy_sprite(self, battle: Battle, enemy_sprite: Image, offset: tuple[int, int]) -> None:
        sprite = self.transform_enemy_sprite(enemy_sprite)

        enemy_bottom_centre_position = self.get_enemy_bottom_centre_position(battle.image)
        # TODO: Use BattlerAltitude in height equation
        position = (
            round(enemy_bottom_centre_position[0] - (sprite.width / 2)) + offset[0] + 2,
            round(enemy_bottom_centre_position[1] - (sprite.height / 2)) + 4 + offset[1]
        )

        battle.image.paste(sprite, position, sprite)

    def generate_battle_image(self, filename: str, image: Image, areas: Iterable[str]) -> Image:
        image = image.convert("RGBA")

        regex_result = re.search(r"\d+\.(\d+)", filename)
        if regex_result is None:
            return

        body_id = regex_result.group(1)
        area = self._get_area(areas)
        battle = self.battles[area]

        self.add_player_sprite(battle, image, self.spriteOffsets[body_id].player_offset)
        self.add_enemy_sprite(battle, image, self.spriteOffsets[body_id].enemy_offset)

        battle = battle.image.resize(
            (battle.image.width * 3, battle.image.height * 3),
            resample=Resampling.NEAREST,
        )

        return battle

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
