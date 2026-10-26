# 7 Days to Die mods

This repo is Ken's mods for 7 Days to Die (7DTD). Most mods are XML modlets. Some are C# mods that ship a Harmony DLL.

## Layout

Each mod is one top-level folder. The folder name matches the `Name` in that mod's `ModInfo.xml`.

A mod folder contains:

- `ModInfo.xml` with `Name`, `DisplayName`, `Version`, `Description`, and `Author`
- `Config/*.xml` — XPath patches for the game's XML
- `Harmony/` — an optional C# project, only when the mod needs a DLL

`scripts`, `.github`, `dist`, and `worlds` belong to the repo, not to the game. `worlds/` holds generators. The world they build is still a top-level folder.

`ModInfo.xml` looks like this:

```xml
<xml>
  <Name value="ModName" />
  <DisplayName value="Mod Name" />
  <Version value="1.0" />
  <Description value="What this mod changes." />
  <Author value="Ken" />
</xml>
```

Older mods can use a `<ModInfo>` root instead of `<xml>`. The same fields are required.

## Install

Unzip the mod folder into the game's `Mods/` directory.

XML-only modlets are server-side friendly. DLL mods need EAC off.

CulDeSac is a world, not a modlet. Install it with `CulDeSac/INSTALL.md`. It goes in the server's `Data/Worlds/` folder, not in `Mods/`.

## Releases

Zips are named `ModName-vX.Y.zip`. The version is the `Version` in `ModInfo.xml`, so version `1.2` of `ModName` is `ModName-v1.2.zip`.

From the repo folder, this builds the zip and puts it in `dist/`:

```bash
python scripts/package.py ModName
```

The mod folder is the top folder inside the zip. Unzipping into `Mods/` gives you `Mods/ModName/`.

This checks every mod (XML is well formed, and `ModInfo.xml` has the required fields):

```bash
python scripts/validate.py
```

## Mods

| Mod | Version | Description |
| --- | ------- | ----------- |
| CulDeSac | 0.1 | Three pine-forest houses on a cul-de-sac. See `CulDeSac/INSTALL.md`. |
