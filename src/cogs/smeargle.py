import io
import logging
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


class BattleImageCreator:
    def __init__(self):
        self.enemySpritePos = (290, 19)  # TODO: Make these work off the dynamic base positions
        self.playerSpritePos = (-20, 30)  # TODO: Make these work off the dynamic base positions
        self.basePath = Path("smeargle-data")
        self.backgrounds = self._generate_bases(self.basePath)
        self.offsets = self._generate_offsets()

    def _generate_offsets(self) -> dict[Any, Offset]:
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

    def _generate_bases(self, base_path: Path | str) -> dict[str, Image]:
        areas = [child for child in Path(base_path, "images").iterdir() if child.is_dir()]

        backgrounds = {}
        for area in areas:
            player_base = Path(area, "player-base.png")
            enemy_base = Path(area, "enemy-base.png")
            background = Path(area, "background.png")

            if any((not player_base.is_file(), not enemy_base.is_file(), not background.is_file())):
                logging.warning(f"{area} is missing a player-base.png, enemy-base.png or background.png")
                continue

            backgrounds[area.name] = self._generate_base(player_base, enemy_base, background)

        return backgrounds

    def _generate_base(self, player_base_path: Path, enemy_base_path: Path, background_path: Path):
        player_base = self.open_image(player_base_path)
        enemy_base = self.open_image(enemy_base_path)
        background = self.open_image(background_path)

        player_base_position = (-75, 303 - player_base.height)
        enemy_base_position = (248, 112)

        background.paste(player_base, player_base_position, player_base)
        background.paste(enemy_base, enemy_base_position, enemy_base)

        return background

    def add_player_sprite(self, background: Image, player_sprite: Image, offset: tuple[int, int]):
        sprite = self.transform_player_sprite(player_sprite)

        # TODO: position is player_base_position + generic_offset + sprite_specific_offset
        position = (
            self.playerSpritePos[0] + offset[0],
            self.playerSpritePos[1] + offset[1],
        )

        background.paste(sprite, position, sprite)

    def add_enemy_sprite(self, background: Image, enemy_sprite: Image, offset: tuple[int, int]):
        sprite = self.transform_enemy_sprite(enemy_sprite)

        # TODO: position is player_base_position + generic_offset + sprite_specific_offset
        position = (
            self.enemySpritePos[0] + offset[0],
            self.enemySpritePos[1] + offset[1],
        )

        background.paste(sprite, position, sprite)

        return background

    def generate_battle_image(self, filename: str, image: Image, areas: Iterable[str]) -> Image:
        image = image.convert("RGBA")

        regex_result = re.search(r"\d+\.(\d+)", filename)
        if regex_result is None:
            return

        body_id = regex_result.group(1)
        area = self._get_area(areas)
        background = self.backgrounds[area].copy()

        self.add_player_sprite(background, image, self.offsets[body_id].player_offset)
        self.add_enemy_sprite(background, image, self.offsets[body_id].enemy_offset)

        background = background.resize((background.width * 3, background.height * 3), resample=Resampling.NEAREST)

        return background

    def _get_area(self, areas):
        for area in areas:
            if area in self.backgrounds.keys():
                return area

        return random.choice(list(self.backgrounds.keys()))

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


async def setup(bot: Bot):
    await bot.add_cog(Smeargle(bot))
