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


BLOG = "https://mosheinternacional.com/"


def fetch_articles(previous):
    """Artigos do blog da Moshe (blog-postagens.json). Se falhar, mantém os anteriores."""
    try:
        posts = json.loads(http(BLOG + "blog-postagens.json"))
        out = []
        for p in posts:
            dd, mm, yyyy = p["data"].split("/")
            out.append({
                "id": p["arquivo"],
                "title": p["titulo"],
                "date": f"{yyyy}-{mm}-{dd}T12:00:00+00:00",
                "url": BLOG + p["arquivo"],
            })
        return out or previous
    except Exception as e:
        print(f"Artigos: falha ao ler o blog ({e}); mantendo os anteriores")
        return previous


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

    # Posição original na playlist (usada nos links) + data de publicação de cada vídeo.
    for i, v in enumerate(unique, 1):
        v["pos"] = i
    cached = {}
    if OUT.exists():
        try:
            for o in json.loads(OUT.read_text(encoding="utf-8")).get("videos", []):
                if o.get("date"):
                    cached[o["id"]] = o["date"]
        except json.JSONDecodeError:
            pass
    for v in unique:
        v["date"] = cached.get(v["id"], "")
        if not v["date"]:
            try:
                page = http("https://www.youtube.com/watch?v=" + v["id"])
                m = re.search(r'"publishDate":"([^"]+)"', page)
                v["date"] = m.group(1) if m else ""
            except Exception as e:  # sem data: vai para o fim da lista
                print(f"Sem data para {v['id']}: {e}")
        v.pop("duration", None)
    # Mais recente primeiro; sem data ficam no fim, na ordem da playlist.
    def ts(d):
        try:
            return datetime.fromisoformat(d).timestamp()
        except ValueError:
            return 0.0
    unique.sort(key=lambda v: ts(v["date"]), reverse=True)  # estável: empates seguem a playlist

    # Evita sobrescrever com lista muito menor (falha parcial do YouTube).
    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8")).get("videos", [])
            if len(unique) < len(old) * 0.8:
                sys.exit(f"Lista suspeita ({len(unique)} vs {len(old)}); mantendo a anterior")
        except json.JSONDecodeError:
            pass

    old_articles = []
    if OUT.exists():
        try:
            old_articles = json.loads(OUT.read_text(encoding="utf-8")).get("articles", [])
        except json.JSONDecodeError:
            pass
    articles = fetch_articles(old_articles)

    payload = {
        "playlist_id": PLAYLIST_ID,
        "title": meta.get("title", "Paraguai"),
        "videos": unique,
        "articles": articles,
    }
    # Só reescreve (e muda a data) se algo mudou, para não gerar commits à toa.
    if OUT.exists():
        try:
            cur = json.loads(OUT.read_text(encoding="utf-8"))
            if cur.get("videos") == unique and cur.get("articles") == articles:
                print(f"Sem mudanças ({len(unique)} vídeos, {len(articles)} artigos)")
                return
        except json.JSONDecodeError:
            pass
    payload["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(unique)} vídeos e {len(articles)} artigos gravados")


if __name__ == "__main__":
    main()
