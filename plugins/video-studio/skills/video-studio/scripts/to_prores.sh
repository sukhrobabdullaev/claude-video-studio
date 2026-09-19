#!/usr/bin/env bash
# Convert an alpha overlay (WebM VP9 / PNG sequence / anything) to ProRes 4444 so
# ffmpeg's native decoders keep the alpha channel during render.py compositing.
#   to_prores.sh in.webm out.mov
set -euo pipefail
in="$1"; out="$2"
case "$in" in
  *.webm) dec=(-c:v libvpx-vp9) ;;   # native vp9 decoder drops WebM alpha
  *)      dec=() ;;
esac
ffmpeg -v error -y "${dec[@]}" -i "$in" -c:v prores_ks -profile:v 4444 \
  -pix_fmt yuva444p12le -an "$out"
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height,pix_fmt,nb_frames -of csv=p=0 "$out"
