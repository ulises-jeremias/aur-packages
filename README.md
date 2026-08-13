# aur-packages

> AUR (Arch User Repository) package mirrors for [ulises-jeremias](https://github.com/ulises-jeremias/aur-packages).
>
> This repo mirrors PKGBUILDs that are published to the AUR.
> Each subdirectory is one AUR package.

## Packages

| Package | AUR | Description |
|---------|-----|-------------|
| [agent-toolkit-bin](agent-toolkit-bin/PKGBUILD) | [agent-toolkit-bin](https://aur.archlinux.org/packages/agent-toolkit-bin) | **Canonical** — native V CLI from GitHub Releases |
| [agent-toolkit](agent-toolkit/PKGBUILD) | [agent-toolkit](https://aur.archlinux.org/packages/agent-toolkit) | Optional Python/source package (not the V product) |

## Installation

```bash
# Canonical (native V binary)
yay -S agent-toolkit-bin

# Optional Python/source package
yay -S agent-toolkit

# Manual (any package)
git clone https://aur.archlinux.org/agent-toolkit.git
cd agent-toolkit
makepkg -si
```

## Auto-update mechanism

PKGBUILDs update automatically when a new release tag is pushed to the package repo.
The `update-package.yml` workflow handles any package — pass `package_name` and `version`.

## Adding a new package

1. Create `<package-name>/PKGBUILD` following existing patterns
2. Ensure `source=` uses `https://` URL (GitHub release or PyPI/npm)
3. Add to the table in this README
4. Configure the package repo to dispatch `new-release` events here
5. Register the package on AUR: `git clone ssh://aur@aur.archlinux.org/<package>.git`
