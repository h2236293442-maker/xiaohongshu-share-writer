#!/usr/bin/env python3
"""Generate Xiaohongshu share-post images with an APIMart-compatible API."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


NO_TEXT_RULE = (
    "Absolutely no text anywhere in the image: no words, no letters, no numbers, "
    "no labels, no captions, no logos, no watermark."
)

DEFAULT_STYLE = (
    "Xiaohongshu share-post illustration, cozy scrapbook collage style, warm creamy "
    "background, pastel sticker and paper-cut elements, subtle grain texture, soft "
    "shadows, cute but premium, airy whitespace, minimal clutter, landscape image "
    "area size 896x720 px, keep about 10 percent safe padding around edges, "
    "consistent camera angle and rendering."
)


def load_dotenv() -> None:
    for name in (".env.local", ".env"):
        path = Path.cwd() / name
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def post_json(url: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body[:1000]}") from exc


def extract_pages(markdown: str) -> list[dict[str, Any]]:
    pattern = re.compile(r"(?m)^##\s*(P\d+|最后.*?页|总结页).*?(?=^##\s|\Z)", re.S)
    pages: list[dict[str, Any]] = []
    for match in pattern.finditer(markdown):
        block = match.group(0).strip()
        heading = block.splitlines()[0].lstrip("#").strip()
        if "封面" in heading or "导读" in heading:
            continue
        prompt_match = re.search(r"```text\s*(.*?)```", block, re.S)
        title_match = re.search(r"-\s*标题[:：]\s*(.+)", block)
        content_match = re.search(r"-\s*内容[:：]\s*(.+)", block)
        summaries = re.findall(r"-\s*总结[:：]\s*(.+)", block)
        pages.append(
            {
                "page": heading,
                "title": title_match.group(1).strip() if title_match else heading,
                "content": content_match.group(1).strip() if content_match else block,
                "summary": summaries,
                "source_prompt": prompt_match.group(1).strip() if prompt_match else "",
            }
        )
    return pages


def build_prompt(page: dict[str, Any], text_model: str, base_url: str, api_key: str) -> str:
    source_prompt = page.get("source_prompt", "")
    if source_prompt and NO_TEXT_RULE in source_prompt:
        return source_prompt

    page_content = {
        "title": page.get("title", ""),
        "content": page.get("content", ""),
        "summary": page.get("summary", []),
    }
    payload = {
        "model": text_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Write one concise English image prompt for a Xiaohongshu share-post "
                    "illustration. Keep it visual, concrete, and text-free."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Style lock: {DEFAULT_STYLE}\n"
                    f"Mandatory rule: {NO_TEXT_RULE}\n"
                    f"Page content JSON: {json.dumps(page_content, ensure_ascii=False)}"
                ),
            },
        ],
        "temperature": 0.4,
    }
    data = post_json(f"{base_url.rstrip('/')}/chat/completions", payload, api_key)
    prompt = data["choices"][0]["message"]["content"].strip()
    if NO_TEXT_RULE not in prompt:
        prompt = f"{DEFAULT_STYLE}\n{NO_TEXT_RULE}\nScene: {prompt}"
    return prompt


def generate_image(prompt: str, image_model: str, size: str, quality: str, base_url: str, api_key: str) -> bytes:
    payload = {"model": image_model, "prompt": prompt, "size": size, "quality": quality, "n": 1}
    data = post_json(f"{base_url.rstrip('/')}/images/generations", payload, api_key)
    item = data["data"][0]
    if "b64_json" in item:
        return base64.b64decode(item["b64_json"])
    if "url" in item:
        with urllib.request.urlopen(item["url"], timeout=180) as resp:
            return resp.read()
    raise RuntimeError("Image response does not contain b64_json or url")


def safe_name(value: str, fallback: str) -> str:
    name = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", value).strip("_")
    return name[:60] or fallback


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", help="Path to a Xiaohongshu markdown draft")
    parser.add_argument("--title", help="Single page title")
    parser.add_argument("--content", help="Single page content")
    parser.add_argument("--summary", action="append", default=[], help="Single page summary line, repeatable")
    parser.add_argument("--outdir", help="Output directory")
    args = parser.parse_args()

    api_key = env("APIMART_API_KEY")
    base_url = env("APIMART_BASE_URL", "https://api.apimart.ai/v1")
    text_model = env("APIMART_TEXT_MODEL", "gpt-4o-mini")
    image_model = env("APIMART_IMAGE_MODEL", "gpt-image-2")
    image_size = env("APIMART_IMAGE_SIZE", "1280x1024")
    image_quality = env("APIMART_IMAGE_QUALITY", "medium")

    if args.markdown:
        md_path = Path(args.markdown).expanduser().resolve()
        pages = extract_pages(md_path.read_text(encoding="utf-8"))
        outdir = Path(args.outdir) if args.outdir else md_path.with_suffix("").parent / f"{md_path.stem}_images"
    else:
        if not args.title or not args.content:
            parser.error("Either --markdown or both --title and --content are required")
        pages = [{"page": "single", "title": args.title, "content": args.content, "summary": args.summary}]
        outdir = Path(args.outdir) if args.outdir else Path.cwd() / f"{safe_name(args.title, 'single')}_images"

    if not pages:
        raise SystemExit("No drawable pages found. Check markdown headings and page format.")

    outdir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []

    for index, page in enumerate(pages, start=1):
        prompt = build_prompt(page, text_model, base_url, api_key)
        image = generate_image(prompt, image_model, image_size, image_quality, base_url, api_key)
        stem = f"{index:02d}_{safe_name(page.get('title', ''), f'page_{index}')}"
        png_path = outdir / f"{stem}.png"
        prompt_path = outdir / f"{stem}.prompt.txt"
        meta_path = outdir / f"{stem}.json"
        png_path.write_bytes(image)
        prompt_path.write_text(prompt, encoding="utf-8")
        meta = {
            "page": page.get("page"),
            "title": page.get("title"),
            "prompt": prompt,
            "image": png_path.name,
            "created_at": int(time.time()),
            "model": image_model,
            "size": image_size,
            "quality": image_quality,
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append(meta)
        print(f"saved {png_path}")

    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
