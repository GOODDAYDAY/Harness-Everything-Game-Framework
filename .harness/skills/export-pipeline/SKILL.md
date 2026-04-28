---
name: export-pipeline
description: Use when exporting and distributing Godot games — export presets, platform settings, CI/CD with GitHub Actions
---

# Export Pipeline in Godot 4.3+

All examples target Godot 4.3+ with no deprecated APIs. GDScript is shown first, C# follows where applicable.

> **Related skills:** **godot-testing** for CI/CD test integration, **godot-optimization** for pre-export performance checks, **responsive-ui** for platform-specific resolution settings.

---

## 1. Export Presets

### Creating Presets in the Editor

Open **Project → Export**, click **Add…**, and select the target platform. Each preset maps to one entry in `export_presets.cfg`. You can create multiple presets for the same platform (e.g., a debug build and a release build for Windows).

Required one-time setup per platform:
- **Export Templates** must be downloaded via **Editor → Export Templates**.
- Platform-specific toolchains (Android SDK, Xcode, etc.) must be installed separately.

### export_presets.cfg

Godot writes `export_presets.cfg` to the project root. Commit this file — it is safe and contains no secrets. Secrets (codesigning passwords, keystore passwords) must **never** be committed; use environment variables instead.

Example preset structure (Windows release):

```ini
[preset.0]

name="Windows Desktop"
platform="Windows Desktop"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="build/windows/MyGame.exe"
encryption_include_filters=""
encryption_exclude_filters=""
encrypt_pck=false
encrypt_directory=false

[preset.0.options]

custom_template/debug=""
custom_template/release=""
debug/export_console_wrapper=1
binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
binary_format/architecture="x86_64"
codesign/enable=false
codesign/identity=""
codesign/password=""
codesign/timestamp=true
codesign/timestamp_server_url=""
codesign/digest_algorithm=1
codesign/description=""
codesign/custom_options=PackedStringArray()
application/icon=""
application/console_wrapper_icon=""
application/icon_interpolation=4
application/file_version=""
application/product_version=""
application/company_name=""
application/product_name=""
application/file_description=""
application/copyright=""
application/trademarks=""
application/export_angle=0
application/export_d3d12=0
application/d3d12_agility_sdk_multiarch=true
ssh_remote_deploy/enabled=false
ssh_remote_deploy/host="user@host_ip"
ssh_remote_deploy/port="22"
ssh_remote_deploy/extra_args_ssh=""
ssh_remote_deploy/extra_args_scp=""
ssh_remote_deploy/run_script="#!/usr/bin/env bash\nexport DISPLAY=:0\n\"{temp_dir}/{exe_name}\" {cmd_args}"
ssh_remote_deploy/cleanup_script="#!/usr/bin/env bash\nkill $(pgrep -x -f \"{temp_dir}/{exe_name} {cmd_args}\")\nrm -rf \"{temp_dir}\""
```

> Godot regenerates `export_presets.cfg` on every editor save. Do not hand-edit it while the editor is open.

---

## 2. Platform-Specific Settings

| Platform  | Key Setting / Consideration                                                                                                                      |
|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| **Windows** | Set `application/icon` (.ico file). Codesigning requires a `.pfx` certificate; set `codesign/enable=true` and supply `codesign/identity` + `codesign/password` via env vars. Without codesigning, Windows SmartScreen will warn users. |
| **Linux**   | No codesigning required. After export, run `chmod +x MyGame.x86_64` on the binary. Ship as a tarball or AppImage for distribution. |
| **macOS**   | Requires notarization for Gatekeeper to allow launch without warning. Set `codesign/enable=true` and `notarization/enable=true`. Provide the `codesign/identity` (Apple Developer ID). The `Info.plist` entries (bundle ID, version, display name, privacy usage descriptions) are set under `application/*` options in the preset. Notarization is done post-export via `xcrun notarytool`. |
| **Web**     | Requires `SharedArrayBuffer` for multi-threading — the web server must send `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` headers. Disable threads (`rendering/threads/thread_model=0`) if hosting on a server you cannot configure. Exported output is a `.html` + `.js` + `.wasm` + `.pck` bundle. |
| **Android** | Requires a keystore for release signing. Set `keystore/release` to the `.keystore` path and supply `keystore/release_user` + `keystore/release_password` via env vars. Declare permissions in the preset under `permissions/*`. Set `package/unique_name` to a reverse-DNS string (e.g., `com.studio.mygame`). |
| **iOS**     | Requires a valid Apple provisioning profile (`.mobileprovision`). Set `application/bundle_identifier`, `codesign/identity`, and `application/provisioning_profile`. Distribution builds require an App Store distribution certificate. |

---

## 3. Export from CLI

Run Godot in headless mode to export without opening the GUI. This is the standard approach for CI/CD.

### Release Export

```bash
godot --headless --export-release "Windows Desktop" build/windows/MyGame.exe
```

### Debug Export

```bash
godot --headless --export-debug "Windows Desktop" build/windows/MyGame.exe
```

### Export .pck Only (no executable)

Use `--export-pack` when you only want to ship updated game data alongside a fixed engine binary (e.g., DLC or patch distribution):

```bash
godot --headless --export-pack "Windows Desktop" build/windows/MyGame.pck
```

### Key CLI flags

| Flag | Purpose |
|------|---------|
| `--headless` | No display server; required for server/CI environments |
| `--export-release "Preset Name" path` | Export using release template |
| `--export-debug "Preset Name" path` | Export using debug template |
| `--export-pack "Preset Name" path` | Export .pck resource pack only |
| `--quit-after N` | Quit after N milliseconds (rarely needed for export) |

> The preset name in the CLI flag must match `name=` in `export_presets.cfg` exactly, including capitalisation and spaces.

---

## 4. CI/CD with GitHub Actions

Full workflow exporting Windows (.exe), Linux (.x86_64), and Web (.html) builds on every push to `main` and on tagged releases.

```yaml
# .github/workflows/export.yml
name: Export Godot Game

on:
  push:
    branches: [main]
  release:
    types: [published]

env:
  GODOT_VERSION: "4.3"
  EXPORT_NAME: "MyGame"

jobs:
  export:
    name: Export — ${{ matrix.preset }}
    runs-on: ubuntu-latest

    strategy:
      fail-fast: false
      matrix:
        include:
          - preset: "Windows Desktop"
            artifact: windows
            output_path: build/windows/MyGame.exe

          - preset: "Linux/X11"
            artifact: linux
            output_path: build/linux/MyGame.x86_64

          - preset: "Web"
            artifact: web
            output_path: build/web/index.html

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0   # needed for git describe (versioning)

      - name: Set up Godot ${{ env.GODOT_VERSION }}
        uses: chickensoft-games/setup-godot@v2
        with:
          version: ${{ env.GODOT_VERSION }}
          use-dotnet: false   # set true for C# projects
          include-templates: true

      - name: Create output directory
        run: mkdir -p $(dirname ${{ matrix.output_path }})

      - name: Inject version from git tag
        run: |
          VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo "0.0.0-dev")
          echo "GAME_VERSION=$VERSION" >> $GITHUB_ENV
          # Patch project.godot so ProjectSettings.get_setting("application/config/version") returns it
          sed -i "s/^config\/version=.*/config\/version=\"$VERSION\"/" project.godot || true

      - name: Export — ${{ matrix.preset }}
        run: |
          godot --headless --export-release "${{ matrix.preset }}" "${{ matrix.output_path }}"

      - name: Mark Linux binary executable
        if: matrix.artifact == 'linux'
        run: chmod +x ${{ matrix.output_path }}

      - name: Upload artifact — ${{ matrix.artifact }}
        uses: actions/upload-artifact@v4
        with:
          name: ${{ env.EXPORT_NAME }}-${{ matrix.artifact }}-${{ env.GAME_VERSION }}
          path: build/${{ matrix.artifact }}/
          if-no-files-found: error
```

> For C# (Mono) projects set `use-dotnet: true` in the `setup-godot` step. The action will install the .NET SDK automatically.

---

## 5. Versioning

### Reading the Version at Runtime

Store the version string in **Project → Project Settings → Application → Config → Version**. Then read it anywhere:

```gdscript
# version_label.gd
extends Label

func _ready() -> void:
    text = "v" + ProjectSettings.get_setting("application/config/version", "dev")
```

```csharp
// VersionLabel.cs
using Godot;

public partial class VersionLabel : Label
{
    public override void _Ready()
    {
        Text = "v" + ProjectSettings.GetSetting("application/config/version", "dev").AsString();
    }
}
```

### Auto-Versioning from Git Tags

Tag your release commit, then inject the version at export time. The CI workflow above does this via `sed`, but you can also run a pre-export GDScript tool (EditorScript) if you prefer to keep it in-engine:

```gdscript
# tools/inject_version.gd  — run with: godot --headless --script tools/inject_version.gd
@tool
extends EditorScript

func _run() -> void:
    var git_output: Array = []
    var exit_code := OS.execute("git", ["describe", "--tags", "--always", "--dirty"], git_output)
    if exit_code != 0:
        push_error("inject_version: git describe failed")
        return

    var version: String = (git_output[0] as String).strip_edges()
    ProjectSettings.set_setting("application/config/version", version)
    var err := ProjectSettings.save()
    if err != OK:
        push_error("inject_version: failed to save project.godot — error %d" % err)
    else:
        print("inject_version: set version to '%s'" % version)
```

Run it as part of a CI step before the export step:

```bash
godot --headless --script tools/inject_version.gd
godot --headless --export-release "Windows Desktop" build/windows/MyGame.exe
```

### Version Tag Convention

Use [Semantic Versioning](https://semver.org/) tags: `v1.2.3`. `git describe` then produces `v1.2.3-4-gabcdef` for commits after a tag, giving you fully traceable builds.

---

## 6. itch.io Deployment

[Butler](https://itch.io/docs/butler/) is the official itch.io CLI for pushing builds.

### Install Butler

```bash
# Linux/macOS
curl -L https://broth.itch.ovh/butler/linux-amd64/LATEST/archive/default -o butler.zip
unzip butler.zip
chmod +x butler

# Or install via GitHub Actions:
# uses: Ayowel/butler-to-itch@v1
```

### Push a Build

```bash
butler push build/windows/ my-studio/my-game:windows
butler push build/linux/   my-studio/my-game:linux
butler push build/web/     my-studio/my-game:web
```

### Channel Naming Convention

| Channel name | Platform |
|---|---|
| `windows` | Windows 64-bit |
| `linux` | Linux 64-bit |
| `macos` | macOS universal |
| `web` | HTML5 / WebGL |
| `android` | Android APK/AAB |

Use `--userversion` to tag the build with your version string:

```bash
butler push build/windows/ my-studio/my-game:windows --userversion "$GAME_VERSION"
```

### GitHub Actions — Deploy to itch.io

Add this job after the export job to push all artifacts to itch.io:

```yaml
  deploy-itch:
    name: Deploy to itch.io
    needs: export
    runs-on: ubuntu-latest
    if: github.event_name == 'release'

    steps:
      - name: Download all build artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - name: Push to itch.io
        uses: Ayowel/butler-to-itch@v1
        with:
          butler_key: ${{ secrets.BUTLER_API_KEY }}
          itch_user: my-studio
          itch_game: my-game
          version: ${{ github.ref_name }}
          files: |
            windows:artifacts/${{ env.EXPORT_NAME }}-windows-*/
            linux:artifacts/${{ env.EXPORT_NAME }}-linux-*/
            web:artifacts/${{ env.EXPORT_NAME }}-web-*/
```

Store your butler API key (from <https://itch.io/user/settings/api-keys>) as a GitHub Actions secret named `BUTLER_API_KEY`.

---

## 7. Steam Deployment

For Steam distribution you need three components working together:

- **Steamworks SDK**: Download from the Steamworks partner site. It is not redistributable — do not commit it to a public repo. Reference it via a local path or a private artifact store in CI.
- **GodotSteam addon**: [GodotSteam](https://godotsteam.com/) is a community addon that wraps the Steamworks C++ SDK for use in GDScript and C#. It provides `Steam.init()`, achievements, stats, UGC, and networking. Install it as a Godot plugin; follow the GodotSteam docs for the exact version matching your Godot and Steamworks SDK versions.
- **Depot configuration**: In Steamworks Partner, define one depot per platform (Windows, Linux, macOS). Each depot maps to a set of files from your export output. The `steamcmd` CLI uploads depots to Steam using `app_build` scripts. Builds are staged in a local `content/` folder and pushed with `steamcmd +run_app_build app_build.vdf`.

Steam integration is outside the scope of the export pipeline itself — refer to the GodotSteam documentation and Steamworks SDK guides for full setup.

---

## 8. Checklist

- [ ] Export templates downloaded for the target Godot version (Editor → Export Templates)
- [ ] `export_presets.cfg` committed to version control
- [ ] Secrets (keystore passwords, codesign passwords, API keys) stored in env vars or CI secrets, never in the file
- [ ] Each preset has a unique `name=` that matches the CLI `--export-release` argument exactly
- [ ] Output directories created before the export command runs (`mkdir -p`)
- [ ] Linux binary marked executable after export (`chmod +x`)
- [ ] `application/config/version` in project.godot is populated at export time from a git tag
- [ ] Web export: hosting server sends `COOP` + `COEP` headers if threads are enabled
- [ ] Android release preset uses a signed keystore, not the debug keystore
- [ ] macOS builds intended for distribution are codesigned and notarized
- [ ] Artifacts are uploaded per-platform in CI so individual platform builds can be downloaded
- [ ] itch.io channels follow the naming convention (windows, linux, macos, web, android)
- [ ] Butler API key stored as a CI secret, not hardcoded
- [ ] Steam depot configs are kept out of public repositories
