#!/bin/sh
# Démarre SSH + Nginx, sème quelques lignes de logs puis génère du trafic continu.
set -e

/usr/sbin/sshd

nginx -g 'daemon off;' &
NGINX_PID=$!

# Attendre que Nginx écoute, puis semer quelques requêtes (logs immédiats)
sleep 1
for i in 1 2 3 4 5 6 7 8; do
    curl -s -o /dev/null "http://localhost/seed/$i" || true
done

# Trafic continu en arrière-plan (nouvelles lignes toutes les ~3 s)
( while true; do
    curl -s -o /dev/null "http://localhost/page/$((RANDOM % 5))" 2>/dev/null || true
    sleep 3
  done ) &

wait "$NGINX_PID"
