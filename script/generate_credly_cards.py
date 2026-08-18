#!/usr/bin/env python3
"""
Generates credly-dark.svg / credly-light.svg — badge cards styled to match
the profile banner (same palette + monospace terminal aesthetic).

Usage (in CI):
    python3 generate_credly_cards.py <credly_username> --out-dir .

Fetches https://www.credly.com/users/<username>/badges.json (public,
no auth needed) and renders one card per badge, each linking to its
public Credly verification page.
"""
import json
import sys
import argparse
import urllib.request

PALETTES = {
    "dark": dict(BG="#0A101F", PANEL="#0D1424", BORDER="#1E293B",
                 CHROME="#22D3EE", TEXT="#F8FAFC", DIM="#64748B", ACCENT="#10B981"),
    "light": dict(BG="#F8FAFC", PANEL="#FFFFFF", BORDER="#CBD5E1",
                  CHROME="#0891B2", TEXT="#0F172A", DIM="#94A3B8", ACCENT="#10B981"),
}

CARD_W, CARD_H = 140, 172
IMG_SIZE = 96
COLS = 6
GAP = 14
PAD = 28
HEADER_H = 56


def fetch_badges(username):
    url = f"https://www.credly.com/users/{username}/badges.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    badges = data.get("data", data if isinstance(data, list) else [])
    out = []
    for b in badges:
        name = (b.get("badge_template") or {}).get("name") or b.get("name") or "Badge"
        image_url = (
            b.get("image_url")
            or (b.get("image") or {}).get("url")
            or (b.get("badge_template") or {}).get("image_url")
        )
        badge_id = b.get("id") or b.get("uuid") or ""
        public_url = f"https://www.credly.com/badges/{badge_id}" if badge_id else "https://www.credly.com/"
        if image_url:
            out.append({"name": name, "image_url": image_url, "public_url": public_url})
    return out


def load_mock(path):
    data = json.load(open(path))
    out = []
    for i, b in enumerate(data["data"]):
        out.append({
            "name": b["badge_template"]["name"],
            "image_url": f"mock{i+1}.png",   # local file, QA only
            "public_url": f"https://www.credly.com/badges/{b['id']}",
        })
    return out


def wrap_text(text, max_chars=18):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:2]


def build_svg(badges, theme):
    pal = PALETTES[theme]
    n = len(badges)
    cols = min(COLS, max(1, n))
    rows = (n + cols - 1) // cols
    W = PAD * 2 + cols * CARD_W + (cols - 1) * GAP
    H = HEADER_H + PAD + rows * CARD_H + (rows - 1) * GAP + PAD

    parts = []
    parts.append(f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
                  f'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                  f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">')
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="14" fill="{pal["BG"]}" stroke="{pal["BORDER"]}"/>')
    parts.append(f'<text x="{PAD}" y="34" font-size="13" letter-spacing="2" fill="{pal["CHROME"]}">CREDLY.BADGES</text>')
    parts.append(f'<text x="{W-PAD}" y="34" font-size="12" fill="{pal["DIM"]}" text-anchor="end">{n} earned</text>')
    parts.append(f'<line x1="{PAD}" y1="44" x2="{W-PAD}" y2="44" stroke="{pal["BORDER"]}"/>')

    for i, b in enumerate(badges):
        col = i % cols
        row = i // cols
        x = PAD + col * (CARD_W + GAP)
        y = HEADER_H + row * (CARD_H + GAP)
        parts.append(f'<a href="{b["public_url"]}" target="_blank">')
        parts.append(f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="10" '
                      f'fill="{pal["PANEL"]}" stroke="{pal["BORDER"]}"/>')
        img_x = x + (CARD_W - IMG_SIZE) / 2
        img_y = y + 12
        parts.append(f'<image href="{b["image_url"]}" x="{img_x}" y="{img_y}" '
                      f'width="{IMG_SIZE}" height="{IMG_SIZE}" preserveAspectRatio="xMidYMid meet"/>')
        lines = wrap_text(b["name"])
        ty = img_y + IMG_SIZE + 16
        for line in lines:
            parts.append(f'<text x="{x + CARD_W/2}" y="{ty}" font-size="10.5" fill="{pal["TEXT"]}" '
                          f'text-anchor="middle">{line}</text>')
            ty += 13
        parts.append('</a>')

    parts.append('</svg>')
    return "".join(parts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("username", nargs="?")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--out-dir", default=".")
    args = ap.parse_args()

    badges = load_mock("mock_badges.json") if args.mock else fetch_badges(args.username)
    if not badges:
        print("No public badges found — check the Credly username and that badges are public.", file=sys.stderr)
        sys.exit(1)

    for theme in ("dark", "light"):
        svg = build_svg(badges, theme)
        with open(f"{args.out_dir}/credly-{theme}.svg", "w") as f:
            f.write(svg)
        print(f"wrote credly-{theme}.svg ({len(svg)} bytes, {len(badges)} badges)")
