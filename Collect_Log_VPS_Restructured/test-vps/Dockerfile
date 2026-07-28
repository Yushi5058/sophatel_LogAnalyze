# Faux VPS de test (RM-33) : Nginx + serveur SSH, adressable, pour valider la
# collecte SSH/SFTP réelle du projet (au-delà du mode mock).
FROM nginx:1.27-alpine

# Serveur SSH + utilisateur de test (sophatel/sophatel), auth par mot de passe.
RUN apk add --no-cache openssh bash curl \
 && ssh-keygen -A \
 && mkdir -p /run/sshd \
 && adduser -D -s /bin/sh sophatel \
 && echo "sophatel:sophatel" | chpasswd \
 && sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
 && sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

# Nginx : format de log « sophatel » (avec request_time) écrit dans un VRAI
# fichier (les images officielles renvoient access.log vers stdout par défaut).
COPY nginx.conf /etc/nginx/nginx.conf
RUN rm -f /var/log/nginx/access.log \
 && touch /var/log/nginx/access.log \
 && chmod 644 /var/log/nginx/access.log

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 22 80
ENTRYPOINT ["/entrypoint.sh"]
