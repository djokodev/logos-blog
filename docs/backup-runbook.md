# Sauvegardes et restauration (LOGOS)

> Contexte : le 2 octobre 2026 le VPS a été réinitialisé par erreur. Le blog a pu être
> restauré grâce aux copies hors serveur (Cloudflare R2 + Mac). Ce document décrit le
> dispositif renforcé mis en place ensuite.

## Les 4 couches

| Couche | Où | Fréquence | Rétention |
|---|---|---|---|
| 1. Sauvegarde locale | VPS `/root/backups/logos-backend` | tous les jours à 02:30 | 30 |
| 2. Copie hors serveur | Cloudflare R2 `logos-backups/prod/weekly/` | tous les jours (après la 1) | 30 |
| 3. Copie sur le Mac | `~/Backups/logos-backend` (launchd, 10:00) | tous les jours | 12 |
| 4. Sauvegarde avant déploiement | VPS + R2 | à chaque `scripts/deploy.sh` | idem |

Chaque sauvegarde contient :

- `db.sql.gz` — dump PostgreSQL complet (articles, révisions, utilisateurs, vues) ;
- `media.tar.gz` — toutes les images téléversées ;
- `content.json.gz` — **export portable** du contenu (articles, catégories, tags, images, vues),
  réimportable même sur une autre version de PostgreSQL ou une base neuve ;
- `checksums.sha256` et `manifest.json`.

## Surveillance (à ne pas oublier)

Le problème de 2026 : la sauvegarde échouait en silence depuis juin. Désormais, si
`HEALTHCHECK_URL` est renseigné dans `/root/logos/.env`, le script prévient
healthchecks.io au début, au succès et en cas d'échec. Sans succès pendant plus de 26 h,
une alerte part par email / Telegram / WhatsApp.

1. Créer un compte gratuit sur https://healthchecks.io
2. Créer un check « LOGOS backup », période 1 jour, tolérance 2 h
3. Copier l'URL de ping dans `/root/logos/.env` : `HEALTHCHECK_URL=https://hc-ping.com/xxxx`

## Commandes utiles (sur le VPS)

```bash
cd /root/logos
bash scripts/backup/backup_weekly.sh          # sauvegarde manuelle
bash scripts/backup/restore_test.sh latest    # test de restauration (base temporaire)
tail -50 /var/log/logos-backup.log            # journal
crontab -l                                    # planification
```

## Restauration complète sur un serveur neuf

1. Préparer le serveur (Docker, Nginx, Certbot) et cloner le dépôt dans `/root/logos`.
2. Recréer `/root/logos/.env` à partir de `.env.example` (nouveaux secrets) et des clés R2.
3. Récupérer la dernière sauvegarde (R2 ou `~/Backups/logos-backend` du Mac) dans `/root/restore`.
4. Créer les conteneurs et démarrer uniquement la base :
   ```bash
   docker compose build web && docker compose create && docker compose up -d db
   ```
5. Restaurer la base, puis les images :
   ```bash
   gunzip -c /root/restore/db.sql.gz | docker compose exec -T db psql -U logos_user -d logos_db
   docker run --rm -v logos_media_volume:/data -v /root/restore:/backup alpine sh -c "tar -xzf /backup/media.tar.gz -C /data"
   ```
6. `docker compose up -d`, puis configurer Nginx + certificat (voir `docs/deployment.md`).

### Variante : restaurer seulement le contenu (base neuve)

```bash
docker compose up -d
gunzip -c content.json.gz > /tmp/content.json
docker compose cp /tmp/content.json web:/tmp/content.json
docker compose exec web python manage.py import_content /tmp/content.json --dry-run   # simulation
docker compose exec web python manage.py import_content /tmp/content.json
docker compose exec web python manage.py createsuperuser
```

## Vérifications après restauration

- [ ] `docker compose ps` : `db`, `web`, `nginx` démarrés
- [ ] l'accueil et un article s'affichent avec leurs images
- [ ] connexion à `/cms/` possible
- [ ] `bash scripts/backup/backup_weekly.sh` passe, puis `restore_test.sh latest`

## Rotation des clés R2

1. Créer une nouvelle clé dans Cloudflare R2 (même bucket).
2. Mettre à jour `/root/logos/.env` **et** `~/.config/logos-backup/env` sur le Mac.
3. Lancer une sauvegarde manuelle, puis supprimer l'ancienne clé.
