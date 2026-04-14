#!/bin/sh
set -e
P="${PORT:-8080}"
sed "s/__PORT__/${P}/g" /tmp/default.conf.tpl > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
