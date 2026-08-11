# Local publishing workflow

This zero-base pipeline turns a rights-approved PDF or ordered PNG/JPEG directory into two deterministic VPM packages: a versioned issue and a `latest` issue.

## Prerequisites

- Install `uv`.
- Use Python 3.11 or newer (`uv` provisions the environment).
- Obtain explicit redistribution approval. The builder refuses manifests unless `rights.redistribution_approved: true` and a statement are present.

The source is treated as read-only. Generated pages are JPEG, preserve aspect ratio, and use manifest-controlled `max_dimension` and `jpeg_quality`. For an image directory, declare the cover explicitly. `affinity_spreads` converts Affinity Publisher's `2,3,4,5...` files into Udon Magazine's historical `3,2,5,4...` content order; `explicit` accepts an exact filename list. The cover is used only by the cover material and is excluded from `pageTextures`.

For a PDF exported as front cover, interior pages, and back cover, set `source.back_cover: true`. The final PDF page is then excluded because Udon Magazine uses the cover material for the closed book and requires an even `pageTextures` array. With `page_order: affinity_spreads`, only the interior is reordered (`3,2,5,4...`); both covers remain outside that spread pairing.

Use separate versions for the two products. A fixed issue normally begins at `output.version: 1.0.0`. The shared `latest` package must advance for every issue, for example `output.latest_version: 16.0.0` for Vol.16 and `17.0.0` for Vol.17.

## Commands

```sh
uv sync
uv run platform-book prepare examples/book.yaml
uv run platform-book build examples/book.yaml
uv run platform-book verify dist/vol16/packages/net.omoi0kane.platform-magazine.vol16 \
  --zip dist/vol16/zips/net.omoi0kane.platform-magazine.vol16-1.0.0.zip
uv run platform-book stage-release examples/book.yaml --target <merged-commit-sha>
uv run pytest
```

`prepare` creates reviewable normalized pages in a sibling `<output>-prepared-pages` directory by default. Keeping this outside the build output allows the documented `prepare` → `build` sequence without mixing review files into managed artifacts. `build` recreates only the manifest's output directory, then creates:

- `packages/<volume-id>/` and its deterministic ZIP;
- `packages/<latest-id>/` and its deterministic ZIP;
- `resolved-manifest.yaml`, `hashes.json`, `validation.md`, and `contact-sheet.jpg`;
- `README-latest.md`, recording the latest-package design.

The ZIP has sorted entries, fixed 1980-01-01 timestamps, normalized permissions, and `package.json` at its root. Unity GUIDs are the first 32 hexadecimal characters of SHA-256 over `package ID + NUL + package-relative path`.

## Latest-package MVP

The latest package is deliberately **self-contained**: its package, pages, metas, material, and active prefab are generated under the latest package ID. Duplicating assets avoids fragile install-order and alias behavior. A dependency-only alias can follow after testing that model in Unity.

## Validation and release gate

Local validation checks manifest/domain rules, rights, page continuity and order, metas, unique GUIDs, prefab page references/count, active generated root, package identity/version, material-to-cover resolution, bundled license, ZIP layout/order, source-file exclusion, and configurable warning/hard ZIP size thresholds. Rebuild cleanup is marker-guarded and refuses to delete an existing unmanaged output directory.

**Unity Editor import or Unity batchmode validation is not performed by this local Python pipeline. It remains an external release gate before publishing.** Import both packages into supported VRChat Worlds projects, inspect the prefab/material in Unity, test page navigation, and only then publish through the separately controlled release workflow.

`stage-release` is a dry-run unless `--execute` is supplied. Execution creates two **draft** GitHub Releases only; it never publishes them. Public release still requires the checklist and explicit user approval.

Tags are package-specific (`vol16-v1.0.0`, `latest-v16.0.0`). Neither version/tag may be reused.
