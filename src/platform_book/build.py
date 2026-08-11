from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import pymupdf
import yaml
from PIL import Image, ImageDraw, ImageOps

from .errors import ValidationError
from .guid import unity_guid
from .inputs import order_book_images
from .manifest import Manifest, load_manifest
from .prepare import pad_odd_content_with_blank, pdf_source_page_order, prepare
from .verify import Verification, verify_package
from .ziputil import deterministic_zip

_TEMPLATE = Path(__file__).resolve().parents[2] / "templates/Platform_vol15.prefab.tmpl"
_LICENSE = Path(__file__).resolve().parents[2] / "LICENSE"
_OUTPUT_MARKER = ".platform-book-output"


@dataclass(frozen=True)
class Product:
    package_id: str
    package_dir: Path
    zip_path: Path


@dataclass(frozen=True)
class BuildResult:
    volume: Product
    latest: Product
    resolved_manifest: Path
    hashes: Path
    validation_report: Path
    contact_sheet: Path


def _asset_meta(guid: str, importer: str = "DefaultImporter") -> str:
    if importer == "TextureImporter":
        return f"""fileFormatVersion: 2
guid: {guid}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 12
  mipmaps:
    mipMapMode: 0
    enableMipMap: 1
    sRGBTexture: 1
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
    flipGreenChannel: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  vTOnly: 0
  ignoreMipmapLimit: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 1
    aniso: 1
    mipBias: 0
    wrapU: 0
    wrapV: 0
    wrapW: 0
  nPOTScale: 1
  lightmap: 0
  compressionQuality: 50
  spriteMode: 0
  spriteExtrude: 1
  spriteMeshType: 1
  alignment: 0
  spritePivot: {{x: 0.5, y: 0.5}}
  spritePixelsToUnits: 100
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 1
  alphaUsage: 1
  alphaIsTransparency: 0
  spriteTessellationDetail: -1
  textureType: 0
  textureShape: 1
  singleChannelComponent: 0
  flipbookRows: 1
  flipbookColumns: 1
  maxTextureSizeSet: 0
  compressionQualitySet: 0
  textureFormatSet: 0
  ignorePngGamma: 0
  applyGammaDecoding: 0
  swizzle: 50462976
  cookieLightType: 0
  platformSettings:
  - serializedVersion: 3
    buildTarget: DefaultTexturePlatform
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 1
    compressionQuality: 50
    crunchedCompression: 1
    allowsAlphaSplitting: 0
    overridden: 0
    ignorePlatformSupport: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  spriteSheet:
    serializedVersion: 2
    sprites: []
    outline: []
    physicsShape: []
    bones: []
    spriteID:
    internalID: 0
    vertices: []
    indices:
    edges: []
    weights: []
    secondaryTextures: []
    nameFileIdTable: {{}}
  mipmapLimitGroupName:
  pSDRemoveMatte: 0
  userData:
  assetBundleName:
  assetBundleVariant:
"""
    main = "\n  mainObjectFileID: 2100000" if importer == "NativeFormatImporter" else ""
    return f"fileFormatVersion: 2\nguid: {guid}\n{importer}:\n  externalObjects: {{}}{main}\n  userData:\n  assetBundleName:\n  assetBundleVariant:\n"


def _material(name: str, cover_guid: str) -> str:
    return f"""%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!21 &2100000
Material:
  serializedVersion: 8
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_Name: {name}_cover
  m_Shader: {{fileID: 46, guid: 0000000000000000f000000000000000, type: 0}}
  m_Parent: {{fileID: 0}}
  m_ModifiedSerializedProperties: 0
  m_ValidKeywords: []
  m_InvalidKeywords: []
  m_LightmapFlags: 4
  m_EnableInstancingVariants: 0
  m_DoubleSidedGI: 0
  m_CustomRenderQueue: -1
  stringTagMap: {{}}
  disabledShaderPasses: []
  m_LockedProperties:
  m_SavedProperties:
    serializedVersion: 3
    m_TexEnvs:
    - _MainTex:
        m_Texture: {{fileID: 2800000, guid: {cover_guid}, type: 3}}
        m_Scale: {{x: 1, y: 1}}
        m_Offset: {{x: 0, y: 0}}
    m_Ints: []
    m_Floats:
    - _Glossiness: 0
    - _Metallic: 0
    m_Colors:
    - _Color: {{r: 1, g: 1, b: 1, a: 1}}
  m_BuildTextureStacks: []
"""


def _prefab(package_id: str, target_name: str, title: str, author: str, page_guids: list[str], material_guid: str) -> str:
    text = _TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("  m_Name: Platform_vol15\n", f"  m_Name: {target_name}\n", 1)
    text = text.replace("      value: Magazine\n", f"      value: {target_name}\n", 1)
    text = re.sub(r'^  title:.*$', f"  title: {json.dumps(title, ensure_ascii=False)}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r'^  author:.*$', f"  author: {json.dumps(author, ensure_ascii=False)}", text, count=1, flags=re.MULTILINE)
    refs = "\n".join(f"  - {{fileID: 2800000, guid: {guid}, type: 3}}" for guid in page_guids)
    text, count = re.subn(r"  pageTextures:\n(?:  - .*\n)+(?=  doublePageCount:)", f"  pageTextures:\n{refs}\n", text, count=1)
    if count != 1:
        raise RuntimeError("reference prefab pageTextures block was not found")
    text = text.replace("e837be709b762d4438d25a62f26bfe25", material_guid)
    return text


def _write_meta(package: Path, relative: str, importer: str = "DefaultImporter") -> None:
    asset = package / relative
    asset.with_name(asset.name + ".meta").write_text(_asset_meta(unity_guid(package.name, relative), importer), encoding="utf-8")


def _build_product(
    manifest: Manifest, package_id: str, version: str, target_name: str, prepared: list[Path]
) -> Product:
    package = manifest.output_directory / "packages" / package_id
    package.mkdir(parents=True)
    page_dir, materials = package / "Runtime/pages", package / "Runtime/materials"
    page_dir.mkdir(parents=True)
    materials.mkdir()
    for relative in ("Runtime", "Runtime/pages", "Runtime/materials"):
        _write_meta(package, relative)

    if len(prepared) < 2:
        raise ValidationError("a book requires one cover and at least one content page")
    cover_source, pages = prepared[0], prepared[1:]
    cover_relative = "Runtime/cover.jpg"
    shutil.copyfile(cover_source, package / cover_relative)
    _write_meta(package, cover_relative, "TextureImporter")
    cover_guid = unity_guid(package_id, cover_relative)
    page_guids: list[str] = []
    for index, source in enumerate(pages, 1):
        relative = f"Runtime/pages/page_{index:03d}.jpg"
        shutil.copyfile(source, package / relative)
        page_guids.append(unity_guid(package_id, relative))
        _write_meta(package, relative, "TextureImporter")

    material_relative = "Runtime/materials/cover.mat"
    material_guid = unity_guid(package_id, material_relative)
    (package / material_relative).write_text(_material(target_name, cover_guid), encoding="utf-8")
    _write_meta(package, material_relative, "NativeFormatImporter")
    prefab_relative = f"Runtime/{target_name}.prefab"
    prefab_path = (package / prefab_relative).resolve()
    runtime_root = (package / "Runtime").resolve()
    if prefab_path.parent != runtime_root:
        raise ValidationError("generated prefab path escapes the package Runtime directory")
    prefab_path.write_text(
        _prefab(package_id, target_name, manifest.title, manifest.author, page_guids, material_guid), encoding="utf-8"
    )
    _write_meta(package, prefab_relative)

    tag_prefix = "latest" if package_id == manifest.latest_id else package_id.rsplit(".", 1)[-1]
    tag = f"{tag_prefix}-v{version}"
    zip_name = f"{package_id}-{version}.zip"
    repository_url = "https://github.com/omoi0kane/platform-magazine"
    package_json = {
        "name": package_id, "displayName": manifest.title + (" (Latest)" if package_id == manifest.latest_id else ""),
        "version": version, "description": f"Self-contained Platform Magazine issue: {manifest.title}",
        "url": f"{repository_url}/releases/download/{tag}/{zip_name}",
        "repo": repository_url,
        "vpmDependencies": {"com.vrchat.worlds": ">=3.8.2", "net.ts7m.udon-magazine": "0.2.0"},
        "author": {"name": manifest.author},
        "unity": "2022.3",
        "license": "SEE LICENSE",
        "licensesUrl": f"{repository_url}/blob/main/LICENSE",
        "keywords": ["VRChat", "Udon", "magazine", "Platform"],
        "platformBook": {
            "targetName": target_name, "pageCount": len(pages),
            "warningSizeMb": manifest.warning_size_mb, "hardSizeMb": manifest.hard_size_mb,
            "selfContainedLatest": package_id == manifest.latest_id,
        },
    }
    (package / "package.json").write_text(json.dumps(package_json, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_meta(package, "package.json")
    shutil.copyfile(_LICENSE, package / "LICENSE")
    _write_meta(package, "LICENSE")
    zip_path = manifest.output_directory / "zips" / zip_name
    deterministic_zip(package, zip_path)
    return Product(package_id, package, zip_path)


def _contact_sheet(pages: list[Path], labels: list[str], destination: Path) -> None:
    if len(pages) != len(labels):
        raise ValidationError("contact-sheet labels do not match prepared pages")
    thumbs: list[Image.Image] = []
    for page in pages:
        with Image.open(page) as image:
            thumb = ImageOps.contain(image.convert("RGB"), (180, 240), Image.Resampling.LANCZOS)
            thumbs.append(thumb.copy())
    columns = min(4, len(thumbs))
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * 200, rows * 270), "white")
    draw = ImageDraw.Draw(sheet)
    for index, thumb in enumerate(thumbs):
        x, y = (index % columns) * 200 + 10, (index // columns) * 270 + 10
        sheet.paste(thumb, (x, y))
        draw.text((x, y + 242), labels[index], fill="black")
    sheet.save(destination, "JPEG", quality=85, optimize=False, progressive=False)


def build(manifest_path: Path | str) -> BuildResult:
    manifest = load_manifest(manifest_path)
    output = manifest.output_directory
    source = manifest.source_path
    if output == source or output in source.parents or source in output.parents:
        raise ValidationError("source and output directories must not contain each other")
    if output.exists():
        marker = output / _OUTPUT_MARKER
        existing = list(output.iterdir())
        if existing and not marker.is_file():
            raise ValidationError(f"output directory is not managed by platform-book: {output}")
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() != manifest.id:
            raise ValidationError(f"output directory belongs to a different manifest: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / _OUTPUT_MARKER).write_text(manifest.id + "\n", encoding="utf-8")
    prepared = prepare(
        manifest.source_path, output / ".prepared", manifest.max_dimension,
        manifest.jpeg_quality, manifest.source_type, manifest.source_cover,
        manifest.page_order, manifest.explicit_pages,
        manifest.source_back_cover,
    )
    prepared = pad_odd_content_with_blank(prepared, manifest.max_dimension, manifest.jpeg_quality)
    volume = _build_product(manifest, manifest.id, manifest.version, manifest.target_name, prepared)
    latest = _build_product(
        manifest, manifest.latest_id, manifest.latest_version, f"{manifest.target_name}_latest", prepared
    )
    checks: list[Verification] = [
        verify_package(volume.package_dir, volume.zip_path), verify_package(latest.package_dir, latest.zip_path)
    ]

    if manifest.source_path.is_dir():
        ordered_sources = order_book_images(
            manifest.source_path, manifest.source_cover, manifest.page_order, manifest.explicit_pages,
        )
        source_order = [path.name for path in ordered_sources[1:]]
        digest = hashlib.sha256()
        for path in ordered_sources:
            digest.update(path.name.encode("utf-8") + b"\0" + path.read_bytes())
        source_sha256 = digest.hexdigest()
    else:
        with pymupdf.open(manifest.source_path) as document:
            ordered_pdf_pages = pdf_source_page_order(
                document.page_count, manifest.page_order, manifest.source_back_cover
            )
        source_order = [f"PDF page {index + 1}" for index in ordered_pdf_pages[1:]]
        source_sha256 = hashlib.sha256(manifest.source_path.read_bytes()).hexdigest()
    filler_count = len(prepared) - 1 - len(source_order)
    if filler_count not in {0, 1}:
        raise ValidationError("generated page count does not match resolved source order")
    display_order = [*source_order, *(["Blank filler"] * filler_count)]
    resolved = {
        **manifest.raw,
        "source": {**manifest.raw["source"], "type": "pdf" if manifest.source_path.is_file() else "images"},
        "output": {**manifest.raw["output"], "directory": str(output), "latest_id": manifest.latest_id,
                   "target_name": manifest.target_name, "max_dimension": manifest.max_dimension,
                   "jpeg_quality": manifest.jpeg_quality, "warning_size_mb": manifest.warning_size_mb,
                   "hard_size_mb": manifest.hard_size_mb},
        "resolved": {
            "content_page_count": len(prepared) - 1, "volume_package": manifest.id,
            "latest_package": manifest.latest_id, "source_sha256": source_sha256,
            "source_page_order": source_order, "generated_blank_pages": filler_count,
        },
    }
    resolved_path = output / "resolved-manifest.yaml"
    resolved_path.write_text(yaml.safe_dump(resolved, sort_keys=False, allow_unicode=True), encoding="utf-8")
    contact = output / "contact-sheet.jpg"
    _contact_sheet(prepared, ["Cover", *display_order], contact)
    (output / "README-latest.md").write_text(
        "# Latest package implementation\n\nThe MVP latest package is deliberately **self-contained** and duplicates the issue assets. "
        "This is robust when installed independently. A dependency-only alias may follow only after Unity validation.\n",
        encoding="utf-8",
    )
    report = output / "validation.md"
    lines = ["# Validation report", "", "Local structural validation passed.", ""]
    for check in checks:
        lines += [f"- `{check.package_id}`: {check.page_count} pages, {check.size_bytes} ZIP bytes"]
        lines += [f"  - Warning: {warning}" for warning in check.warnings]
    lines += ["", "## External gate", "", "Unity Editor import/batchmode validation was not run and remains a required external release gate.", ""]
    report.write_text("\n".join(lines), encoding="utf-8")

    shutil.rmtree(output / ".prepared")
    hash_entries: dict[str, str] = {}
    for path in sorted(p for p in output.rglob("*") if p.is_file() and p.name != "hashes.json"):
        hash_entries[path.relative_to(output).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    hashes = output / "hashes.json"
    hashes.write_text(json.dumps({"algorithm": "sha256", "files": hash_entries}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return BuildResult(volume, latest, resolved_path, hashes, report, contact)
