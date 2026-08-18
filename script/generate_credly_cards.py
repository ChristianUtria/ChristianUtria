#!/usr/bin/env python3
"""
Generates credly-dark.svg / credly-light.svg — certificate-style badge
cards with an auto-rotating carousel (3 cards visible at a time, fades
to the next page on a timer via SMIL — no JS, since GitHub strips
scripts from embedded SVGs).

Usage (in CI):
    python3 generate_credly_cards.py <credly_username> --out-dir .

Fetches https://www.credly.com/users/<username>/badges.json (public,
no auth needed). Only fields Credly actually provides are used — no
invented difficulty/price/duration.
"""
import json
import sys
import argparse
import base64
import urllib.request

PALETTES = {
    "dark": dict(BG="#0A101F", CARD="#0D1424", BORDER="#22304A",
                 CHROME="#22D3EE", TITLE="#93C5FD", TEXT="#F8FAFC",
                 DIM="#64748B", ACCENT="#10B981", RIBBON="#F59E0B"),
    "light": dict(BG="#F8FAFC", CARD="#FFFFFF", BORDER="#CBD5E1",
                  CHROME="#0891B2", TITLE="#1D4ED8", TEXT="#0F172A",
                  DIM="#64748B", ACCENT="#10B981", RIBBON="#F59E0B"),
}

CARD_W, CARD_H = 280, 190
GAP = 20
PAD = 28
HEADER_H = 50
DOTS_H = 26
PER_PAGE = 3

DWELL = 3.5     # seconds a page stays fully visible
TRANS = 0.8     # seconds crossfade to next page


def to_data_uri(image_url):
    req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
        content_type = r.headers.get("Content-Type", "image/png").split(";")[0]
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{content_type};base64,{b64}"


def fetch_badges(username):
    url = f"https://www.credly.com/users/{username}/badges.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    badges = data.get("data", data if isinstance(data, list) else [])
    out = []
    for b in badges:
        tmpl = b.get("badge_template") or {}
        name = tmpl.get("name") or b.get("name") or "Badge"
        description = tmpl.get("description") or b.get("description") or ""
        issuer = ""
        try:
            issuer = tmpl["issuer"]["entities"][0]["entity"]["name"]
        except Exception:
            issuer = (b.get("issuer") or {}).get("name", "")
        issued_at = (b.get("issued_at") or "")[:10]
        image_url = b.get("image_url") or (b.get("image") or {}).get("url") or tmpl.get("image_url")
        badge_id = b.get("id") or b.get("uuid") or ""
        public_url = f"https://www.credly.com/badges/{badge_id}" if badge_id else "https://www.credly.com/"
        if image_url:
            out.append({
                "name": name, "description": description, "issuer": issuer,
                "issued_at": issued_at, "image_url": image_url, "public_url": public_url,
            })
    for b in out:
        try:
            b["image_data_uri"] = to_data_uri(b["image_url"])
        except Exception as e:
            print(f"  warn: could not fetch image for '{b['name']}': {e}", file=sys.stderr)
            b["image_data_uri"] = None
    return out


def load_mock(path):
    data = json.load(open(path))
    out = []
    for i, b in enumerate(data["data"]):
        img_path = f"mock{i+1}.png"
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        out.append({
            "name": b["badge_template"]["name"],
            "description": "Demonstrates practical, hands-on proficiency validated through applied "
                            "exercises and assessments covering the core skill area.",
            "issuer": b.get("issuer", "Credly"),
            "issued_at": "2025-03-14",
            "image_data_uri": f"data:image/png;base64,{b64}",
            "public_url": f"https://www.credly.com/badges/{b['id']}",
        })
    return out


def wrap_text(text, max_chars, max_lines):
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
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:max_chars - 1].rstrip() + "…"
    return lines


def ribbon_icon(cx, cy, color):
    return (
        f'<g transform="translate({cx},{cy})">'
        f'<circle r="10" fill="none" stroke="{color}" stroke-width="2"/>'
        f'<path d="M-4,8 L-6,18 L0,14 L6,18 L4,8" fill="{color}"/>'
        f'<path d="M-3,-3 l2,3 l4,-5" fill="none" stroke="{color}" stroke-width="1.6" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'</g>'
    )


def build_card(b, x, y, pal):
    parts = [f'<a href="{b["public_url"]}" target="_blank">']
    parts.append(f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="14" '
                  f'fill="{pal["CARD"]}" stroke="{pal["BORDER"]}" stroke-width="1.5"/>')

    if b.get("issuer"):
        parts.append(f'<text x="{x+18}" y="{y+24}" font-size="9.5" letter-spacing="1" '
                      f'fill="{pal["DIM"]}">{b["issuer"].upper()}</text>')
    parts.append(ribbon_icon(x + CARD_W - 24, y + 22, pal["RIBBON"]))

    title_lines = wrap_text(b["name"], 26, 2)
    ty = y + 48
    for line in title_lines:
        parts.append(f'<text x="{x+18}" y="{ty}" font-size="15" font-weight="700" '
                      f'fill="{pal["TITLE"]}">{line}</text>')
        ty += 19

    img_box = 46
    img_x = x + CARD_W - img_box - 16
    img_y = y + CARD_H - img_box - 16
    if b.get("image_data_uri"):
        parts.append(f'<rect x="{img_x-4}" y="{img_y-4}" width="{img_box+8}" height="{img_box+8}" '
                      f'rx="8" fill="none" stroke="{pal["BORDER"]}"/>')
        parts.append(f'<image href="{b["image_data_uri"]}" x="{img_x}" y="{img_y}" '
                      f'width="{img_box}" height="{img_box}" preserveAspectRatio="xMidYMid meet"/>')

    if b.get("description"):
        desc_lines = wrap_text(b["description"], 30, 3)
        dy = ty + 8
        for line in desc_lines:
            parts.append(f'<text x="{x+18}" y="{dy}" font-size="10.5" '
                          f'fill="{pal["TEXT"]}" opacity="0.85">{line}</text>')
            dy += 14

    if b.get("issued_at"):
        parts.append(f'<text x="{x+18}" y="{y+CARD_H-16}" font-size="9.5" '
                      f'fill="{pal["DIM"]}">Issued {b["issued_at"]}</text>')

    parts.append('</a>')
    return "".join(parts)


def build_svg(badges, theme):
    pal = PALETTES[theme]
    pages = [badges[i:i + PER_PAGE] for i in range(0, len(badges), PER_PAGE)]
    n_pages = len(pages)
    W = PAD * 2 + PER_PAGE * CARD_W + (PER_PAGE - 1) * GAP
    H = HEADER_H + PAD + CARD_H + PAD + DOTS_H

    cycle = n_pages * (DWELL + TRANS)

    parts = []
    parts.append(f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
                  f'xmlns="http://www.w3.org/2000/svg" '
                  f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">')
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="14" fill="{pal["BG"]}" stroke="{pal["BORDER"]}"/>')
    parts.append(f'<text x="{PAD}" y="32" font-size="13" letter-spacing="2" '
                  f'fill="{pal["CHROME"]}">CERTIFICACIONES</text>')
    parts.append(f'<text x="{W-PAD}" y="32" font-size="12" fill="{pal["DIM"]}" '
                  f'text-anchor="end">{len(badges)} earned</text>')
    parts.append(f'<line x1="{PAD}" y1="40" x2="{W-PAD}" y2="40" stroke="{pal["BORDER"]}"/>')

    page_y = HEADER_H + PAD - 20
    for p_idx, page in enumerate(pages):
        t_on = p_idx * (DWELL + TRANS)
        t_full = t_on + TRANS
        t_off = t_full + DWELL
        t_gone = t_off + TRANS

        def op_at(t):
            if p_idx == 0 and t <= t_on:
                return 1
            if t_on <= t <= t_full:
                return round((t - t_on) / max(t_full - t_on, 1e-6), 3)
            if t_full <= t <= t_off:
                return 1
            if t_off <= t <= t_gone:
                return round(1 - (t - t_off) / max(t_gone - t_off, 1e-6), 3)
            return 0

        times = sorted(set([0, t_on, t_full, t_off, min(t_gone, cycle), cycle]))
        kt_frac = [round(t / cycle, 4) for t in times]
        vals = [str(op_at(t)) for t in times]
        start_op = vals[0]

        parts.append(f'<g opacity="{start_op}">')
        parts.append(f'<animate attributeName="opacity" dur="{cycle:.2f}s" repeatCount="indefinite" '
                      f'keyTimes="{";".join(str(k) for k in kt_frac)}" values="{";".join(vals)}"/>')
        for c_idx, b in enumerate(page):
            cx = PAD + c_idx * (CARD_W + GAP)
            parts.append(build_card(b, cx, page_y, pal))
        parts.append('</g>')

    dots_y = H - DOTS_H / 2
    total_dots_w = n_pages * 16
    dots_x0 = W / 2 - total_dots_w / 2
    for p_idx in range(n_pages):
        t_on = p_idx * (DWELL + TRANS)
        t_full = t_on + TRANS
        t_off = t_full + DWELL
        t_gone = t_off + TRANS

        def dop_at(t):
            if p_idx == 0 and t <= t_on:
                return 1
            if t_on <= t <= t_full:
                return round(0.25 + 0.75 * (t - t_on) / max(t_full - t_on, 1e-6), 3)
            if t_full <= t <= t_off:
                return 1
            if t_off <= t <= t_gone:
                return round(1 - 0.75 * (t - t_off) / max(t_gone - t_off, 1e-6), 3)
            return 0.25

        times = sorted(set([0, t_on, t_full, t_off, min(t_gone, cycle), cycle]))
        kt_frac = [round(t / cycle, 4) for t in times]
        vals = [str(dop_at(t)) for t in times]
        dcx = dots_x0 + p_idx * 16 + 5
        parts.append(f'<circle cx="{dcx:.1f}" cy="{dots_y}" r="4" fill="{pal["CHROME"]}" opacity="{vals[0]}">'
                      f'<animate attributeName="opacity" dur="{cycle:.2f}s" repeatCount="indefinite" '
                      f'keyTimes="{";".join(str(k) for k in kt_frac)}" values="{";".join(vals)}"/></circle>')

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
        print(f"wrote credly-{theme}.svg ({len(svg)} bytes, {len(badges)} badges, "
              f"{(len(badges)+PER_PAGE-1)//PER_PAGE} pages)")
