# Paraguai Ojeda

Site com duas abas: **Vídeos** (playlist *Paraguai* do [canal no YouTube](https://www.youtube.com/@BitcoineLiberdade)) e **Mentoria e Consultoria**.

Playlist: https://www.youtube.com/playlist?list=PL1TShuYSNH-tlBHORUdi7w6r1AdDym2fg

## Como se atualiza sozinho

- O player embutido lê a playlist direto do YouTube (sempre atual).
- Um GitHub Action (`.github/workflows/atualizar.yml`) roda a cada 3 horas, executa `scripts/update_playlist.py` e, se entrou ou saiu vídeo, atualiza `videos.json` com um commit automático.
- Para forçar agora: aba **Actions -> Atualizar playlist -> Run workflow**.

Rodar localmente: `python scripts/update_playlist.py` (sem dependências, sem chave de API).
