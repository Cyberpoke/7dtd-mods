# CulDeSac on the AMP server

This is a finished world for 7 Days to Die **V3.3.0**. It is not a modlet. Do not put it in `Mods/`.

Players do not install anything. The server sends the world when they join.

## Copy it

1. Unzip `CulDeSac-v0.1.zip`. You get a folder named `CulDeSac`.
2. In the AMP file manager, open `294420/Data/Worlds/`.
3. Copy that `CulDeSac` folder into `Worlds`.

This file has to exist when you are done:

`294420/Data/Worlds/CulDeSac/map_info.xml`

`INSTALL.md`, `preview.png`, and `ModInfo.xml` can stay in the folder. The game does not read them.

## Start a new game on it

1. AMP → Configuration → 7 Days to Die → Gameplay Settings.
2. Set **Game World** to `CulDeSac`.
3. Set **Game Name** to a new name, such as `CulDeSac1`. An old save name will not rebuild this world.
4. Leave World Gen Seed and World Gen Size alone. They only apply when Game World is `RWG`.
5. Start the server.

The map is 2048 by 2048, all pine forest. The cul-de-sac is at the center. A red radiation border is only the outer 64 blocks of the map.

## main.ttw

This zip does not include `main.ttw`, and it does not include `dtm_processed.raw` or the `splat*_processed.png` files.

Those processed splat and height files are rebuilt by the game. A Fun Pimps moderator (Riamus) said to delete a processed splat after you edit the source PNG and let the game regenerate it: https://community.thefunpimps.com/threads/edit-heightmap-no-water-in-processed-world.43538/

`main.ttw` is a different file, and its bytes are not documented for V3.3.

- The `main.ttw` inside a **save** (`Saves/<world>/<game name>/`) is created when that game name starts. Do not copy one of those in. A crash can turn that save file into zeros: https://community.thefunpimps.com/threads/fix-for-broken-main-ttw-and-main-ttw-bak-files.13889/
- RWG worlds also ship a small `main.ttw` in the **world** folder. In Alpha 17 the way to make a hand-built world load was to copy that small file from any generated world: https://community.thefunpimps.com/threads/alpha-17b240-quick-guide-to-creating-a-7-days-to-die-world-from-an-external-image.10589/
- Nitrogen reused one stub for every map (2019). Teragon writes one, but Teragon is closed source and its note says "A21.1 compatible," not V3.3. A 2026 generator still calls the format undecoded: https://7d2dmapgen.indifferentketchup.com/

Nothing public writes a real V3.3 `main.ttw`, so this project does not invent one.

If the AMP log says the world will not load because `main.ttw` is missing:

1. Generate any small RWG world once, or use one you already have.
2. Copy only that world's `main.ttw` (the file next to its `map_info.xml`, not the one inside a save) into `294420/Data/Worlds/CulDeSac/`.
3. Start again with a **new** Game Name.

Do not copy that other world's `dtm.raw` or splat files over CulDeSac.

## Houses

Three vanilla bungalows, each 42 by 42, from the game's own list:

- `house_old_bungalow_02` north of the circle, front door facing south
- `house_old_bungalow_03` to the south-east, front door facing west
- `house_old_bungalow_04` to the south-west, front door facing east

`preview.png` is a top-down picture of that layout. White arrows point out the front doors. Yellow dots are the spawn points, on the asphalt apron at the end of the south road.

No driveway parts are placed. Each bungalow's own file asks for a different country-road driveway, and the cul-de-sac driveway parts are a different size. Guessing those offsets would put concrete in the wrong place. The asphalt is the circle in `splat3.png`.

The prefab Y is the pad height (48), with `y_is_groundlevel="true"`, so the game should use each house's own `YOffset` for the basement. `_02` and `_04` are -4. `_03` is -1.

## Checks for you, in game

- The AMP log shows the world loading with no errors.
- You spawn on the pad at the south end of the road, not inside a house and not in radiation.
- The three houses sit on the ground. They are not floating and not buried. Front doors face the circle.
- The circle and the short road south are asphalt.
- The ground around the houses is pine forest. There is no radiation there.
- A second player can join, and their game downloads the world.
