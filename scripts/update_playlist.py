#!/usr/bin/env python3
"""Lê a playlist pública do YouTube e grava videos.json (sem chave de API).

Usado pelo GitHub Action .github/workflows/atualizar.yml e também local:
    python scripts/update_playlist.py
"""
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PLAYLIST_ID = "PL1TShuYSNH-tlBHORUdi7w6r1AdDym2fg"
OUT = Path(__file__).resolve().parent.parent / "videos.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def http(url, data=None):
    headers = {"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def walk(o, found, tokens):
    if isinstance(o, dict):
        l = o.get("lockupViewModel")
        if l and "VIDEO" in str(l.get("contentType")):
            try:
                title = l["metadata"]["lockupMetadataViewModel"]["title"]["content"]
            except KeyError:
                title = ""
            dur = re.findall(r'"text":"(\d+:\d\d(?::\d\d)?)"', json.dumps(l))
            found.append({"id": l.get("contentId"), "title": title, "duration": dur[0] if dur else ""})
            return
        cc = o.get("continuationCommand")
        if cc and cc.get("token"):
            tokens.append(cc["token"])
        for v in o.values():
            walk(v, found, tokens)
    elif isinstance(o, list):
        for v in o:
            walk(v, found, tokens)


def main():
    html = http(f"https://www.youtube.com/playlist?list={PLAYLIST_ID}")
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not m:
        sys.exit("ytInitialData não encontrado")
    data = json.loads(m.group(1))
    meta = data.get("metadata", {}).get("playlistMetadataRenderer", {})
    key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html)
    ver = re.search(r'"INNERTUBE_CONTEXT_CLIENT_VERSION":"([^"]+)"', html)

    videos, tokens = [], []
    walk(data, videos, tokens)
    seen_tokens = set()
    while tokens and key:
        tok = tokens.pop(0)
        if tok in seen_tokens:
            continue
        seen_tokens.add(tok)
        ctx = {"client": {"clientName": "WEB", "clientVersion": ver.group(1) if ver else "2.20240101.00.00", "hl": "pt-BR"}}
        page = json.loads(http(f"https://www.youtube.com/youtubei/v1/browse?key={key.group(1)}",
                               {"context": ctx, "continuation": tok}))
        walk(page, videos, tokens)

    unique, ids = [], set()
    for v in videos:
        if v["id"] and v["id"] not in ids:
            ids.add(v["id"])
            unique.append(v)

    if not unique:
        sys.exit("Nenhum vídeo encontrado; mantendo o videos.json anterior")

    # Evita sobrescrever com lista muito menor (falha parcial do YouTube).
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8")).get("videos", [])
            if len(unique) < len(old) * 0.8:
                sys.exit(f"Lista suspeita ({len(unique)} vs {len(old)}); mantendo a anterior")
        except json.JSONDecodeError:
            pass

    payload = {
        "playlist_id": PLAYLIST_ID,
        "title": meta.get("title", "Paraguai"),
        "videos": unique,
    }
    # Só reescreve (e muda a data) se a lista mudou, para não gerar commits à toa.
    if OUT.exists():
        try:
            if json.loads(OUT.read_text(encoding="utf-8")).get("videos") == unique:
                print(f"Sem mudanças ({len(unique)} vídeos)")
                return
        except json.JSONDecodeError:
            pass
    payload["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(unique)} vídeos gravados")


if __name__ == "__main__":
    main()
