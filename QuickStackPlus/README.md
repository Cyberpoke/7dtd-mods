# Quick Stack Plus

Quick Stack Plus adds three backpack actions for 7 Days to Die **V3.4.0 (b6)**, Steam build **26167630**. It is a small Harmony DLL for a server with Easy Anti-Cheat off. Install the same folder on the dedicated server and on every client.

The server does the move. A client only asks. Distance, ownership, and locks are checked again from the server's copy of the world.

This mod is based on [Quick Stack Nearby](https://github.com/Path-of-7D2D/Quick-Stack-Nearby) by Path-of-7D2D (MIT, commit `cee585d`). See [LICENSE](LICENSE).

## What it does

The toolbelt is never touched. Locked backpack slots are never touched.

1. **Quick stack to nearby boxes.** Tops up existing partial stacks of the same item in player-owned storage within range. It uses the game's own `TryStackItem` rule (same item type, and only while the destination stack still has room). It does not start a new stack in a box.
2. **Matched to my vehicle.** The same top-up, into the player's own vehicle.
3. **Everything to my vehicle.** Moves every unlocked backpack slot into that vehicle. Existing stacks are filled first, then empty unlocked vehicle slots are used.

Range defaults to 20 meters and is **clamped to 20 on the server**, even if `settings.xml` asks for more. The dedicated server's `settings.xml` is the range that is used. Each player's own `settings.xml` supplies their hotkeys.

A storage box counts when `TEFeatureStorage.ItemGrid.PlayerOwned` is set and the player can use it: unlocked, or locked and the player is the owner or on the allowed list. The id checked on a dedicated server is `ClientInfo.InternalId`. A box that anyone currently has open, including the player who asked, is skipped so that open copy cannot write back over the move.

A vehicle counts only when `GetOwner()` is set and equals that same id. `EntityVehicle.IsOwner` is not used, because it returns true for an unowned vehicle. A vehicle with a driver, or with its storage or collect lock held, is skipped. If several of the player's vehicles are in range, the nearest one that is not in use is chosen.

Feedback is a short tooltip, for example `Stacked 37 items into 4 boxes` or `No owned vehicle within 20m`. The server also writes the same line to the log.

## Controls

Three buttons are added on the backpack window, in the vanilla container-control row, to the left of the lock button:

| Button | Action | Default hotkey |
| --- | --- | --- |
| Similar-items down | Nearby boxes | Keypad7 |
| Minibike | Matching stacks into your vehicle | Keypad8 |
| Store-all down | Everything into your vehicle | Keypad9 |

Hotkeys work in game while no text field is focused. Set a key to `None` in `settings.xml` to disable it. Key names are Unity `KeyCode` names. Restart after editing the file.

Console and chat, permission level 0:

```text
qsp nearby
qsp vehicle
qsp all
```

`quickstack` is an alias. In chat this is `/qsp nearby` when the server allows players to run console commands.

## Install

Keep the game's `0_TFP_Harmony` mod installed. Copy this folder into `Mods` on the server and on each client:

```text
Mods/QuickStackPlus/ModInfo.xml
Mods/QuickStackPlus/QuickStackPlus.dll
Mods/QuickStackPlus/settings.xml
Mods/QuickStackPlus/Config/
Mods/QuickStackPlus/README.md
Mods/QuickStackPlus/LICENSE
```

Launch with Easy Anti-Cheat disabled. `ModInfo.xml` sets `SkipWithAntiCheat` so the mod does not load under EAC.

## Other mods on this server

Checked against the public GitHub source of aedenthorn's CraftFromContainers (`aedenthorn/7D2DMods`, `CraftFromContainers.cs`). That mod patches crafting, repair, reload, trader purchase, recipe UI, and `EntityVehicle.takeFuel` / `EntityVehicle.hasGasCan`. Quick Stack Plus does not patch any of those. Its only Harmony patch is `XUiC_BackpackWindow.Init`, which that CraftFromContainers source does not patch. A newer CraftFromContainers build than that GitHub file could still add an `Init` patch; both postfixes can run, but they should not be given the same button id.

StarterBicycle, TFP_CommandExtensions, Xample_MarkersMod, ZZZ_HornOpensDoors, and Oak's Pets and Guards are not patched here. This mod does not prefix its folder name, so it does not force a load order. The console command names are `qsp` and `quickstack`.

## Build

No CI. You need a .NET SDK that can build `net48` (SDK 8 works) and the game's managed DLLs. Do not commit those DLLs.

`Managed7D2D` is the directory that contains `Assembly-CSharp.dll` (and the Unity modules next to it). `Harmony7D2D` is the directory that contains the game's `Mods/0_TFP_Harmony/0Harmony.dll`. For the dedicated-server reference set used here, both DLLs live in the same folder.

```bash
dotnet build src/QuickStackPlus.csproj -c Release \
  -p:Managed7D2D="/path/to/managed" \
  -p:Harmony7D2D="/path/to/0_TFP_Harmony" \
  -p:InstallToGame=false
```

The build writes `QuickStackPlus.dll` into this folder. `InstallToGame` stays off unless you also pass `-p:Game7D2D` and `-p:InstallToGame=true`.

The project was built with 0 warnings and 0 errors against the V3.4.0 (b6) assemblies from Steam depot 294421, manifest `2709746199376235989` (build 26167630).

## XUi

`Config/XUi_InGame/windows.xml` appends the three buttons with:

```text
/windows/window[@name='windowBackpack']/rect[@name='header']/rect[@controller='ContainerStandardControls']
```

The button names (`btnToggleLockMode`, `btnSort`, `btnMoveFillAndSmart`, `btnMoveAll`) match `XUiC_BackpackWindow` and `XUiC_ContainerStandardControls` in the 3.4.0b6 `Assembly-CSharp.dll`. The window name, the `header` rect, and the `controller="ContainerStandardControls"` attribute are the layout from the public modding wiki's `XUi_InGame/windows.xml` and from the V3.1 Quick Stack Nearby patch. **The vanilla `Data/Config` XUi files for build 26167630 were not in the reference DLLs, so that xpath and the button positions are not confirmed against those exact files.** If the log says a backpack button was not found, the xpath missed and `qsp` still works.

`Config/Localization.csv` and `ModInfo.xml` are well-formed XML/CSV. `settings.xml` sits next to `ModInfo.xml`, not under `Config/`, so the game's XML patcher does not treat it as a vanilla file.

## In-game checks

These cannot be confirmed from the compile:

- The three buttons appear on the backpack window and do not cover the lock, sort, or currency readout. Nudge the `pos` values in `windows.xml` if they do. Creative mode's trash button sits near these icons.
- Keypad7 / Keypad8 / Keypad9 fire only while you are not typing.
- A locked backpack slot and every toolbelt slot stay put in all three modes.
- Nearby mode fills a partial stack and does not create a new stack, including when the box already contains that item and has an empty slot.
- A different quality that the vanilla stack button will not combine (stack size 1, or a different item type) stays in the backpack.
- A world loot container, a locked box you are not allowed to use, and a box farther than the server range are unchanged.
- An owned vehicle within range gets the match and the move-all actions. An unowned vehicle, someone else's vehicle, a vehicle you are driving, and a vehicle whose storage is open do not.
- With two of your vehicles in range, the nearer free one is used.
- On the dedicated server, a second player cannot lose or duplicate items if they open a box while you stack. A box they already have open is skipped.
- After a remote stack, the backpack and the box or vehicle show the same counts on the client that asked and on the server. The server log line matches the tooltip.

Multiplayer notes: the server applies the last backpack upload (`latestPlayerData.bagData`, sent by the game shortly after each backpack change). Avoid picking up, dropping, or dragging a stack in the same moment as the button. The client then applies the slots the server actually changed.
