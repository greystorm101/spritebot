"""
This parses the game graphics images needed for the Smeargle cog (under smeargle-data/images)

You will need the background, enemy base and player base folders from Infinite Fusion *somewhere* and you can change
the path locations for those in the generate_images call.
"""

import shutil
from pathlib import Path


def generate_images(output_folder: Path, battle_backgrounds_folder: Path, enemy_base_folder: Path,
                    player_base_folder: Path):
    output_folder.mkdir(exist_ok=True)

    for background in battle_backgrounds_folder.iterdir():
        if background.is_dir():
            continue

        area = background.name

        if "_eve" in area or "_night" in area:
            area = area.replace("_eve", "").replace("_night", "")

        enemy_base = Path(enemy_base_folder, area)
        player_base = Path(player_base_folder, area)

        if not enemy_base.exists() or not player_base.exists():
            print(f"Enemy base or player base does not exist for area: {area}")
            continue

        output_subfolder = Path(output_folder, background.stem)
        output_subfolder.mkdir(exist_ok=True)

        shutil.copy(background, Path(output_subfolder, "background.png"))
        shutil.copy(enemy_base, Path(output_subfolder, "enemy-base.png"))
        shutil.copy(player_base, Path(output_subfolder, "player-base.png"))


if __name__ == "__main__":
    output_folder = Path("out")
    battle_backgrounds_folder = Path("battlebg")
    enemy_base_folder = Path("enemybase")
    player_base_folder = Path("playerbase")

    generate_images(output_folder, battle_backgrounds_folder, enemy_base_folder, player_base_folder)
