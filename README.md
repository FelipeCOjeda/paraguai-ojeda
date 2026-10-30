# Vídeos sobre o Paraguai — Moshe Internacional

Centro de informações sobre o Paraguai: vídeos (playlist *Paraguai*) e artigos do blog da Moshe, misturados por data (mais novo primeiro), com o vídeo mais recente em destaque. Página de vídeos (playlist *Paraguai*) com o cabeçalho e os links do site da Moshe Internacional (site, blog, contato, consulta). Destino: videos.mosheinternacional.com.

Playlist: https://www.youtube.com/playlist?list=PL1TShuYSNH-tlBHORUdi7w6r1AdDym2fg

## Como se atualiza sozinho

- O player embutido lê a playlist direto do YouTube (sempre atual).
- Um GitHub Action (`.github/workflows/atualizar.yml`) roda a cada 3 horas, executa `scripts/update_playlist.py` e, se entrou ou saiu vídeo, atualiza `videos.json` com um commit automático.
- Para forçar agora: aba **Actions -> Atualizar playlist -> Run workflow**.

Rodar localmente: `python scripts/update_playlist.py` (sem dependências, sem chave de API).
