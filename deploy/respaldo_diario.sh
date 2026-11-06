#!/bin/sh
# Crea una copia de seguridad comprobada al día y conserva las más recientes.
# Se ejecuta dentro del contenedor "respaldos" de docker-compose.yml.
set -u

HORA="${RESPALDO_HORA:-21}"
CONSERVAR="${RESPALDO_CONSERVAR:-30}"
CARPETA=/backups
export TZ="${CLINICA_TIMEZONE:-UTC}"
export PGPASSWORD="$POSTGRES_PASSWORD"

# El administrador ve en pantalla si las copias fallan. No poder avisar no detiene las copias.
registrar_estado() {
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -qAtc "UPDATE estado_copias SET $1 = now()" > /dev/null 2>&1 \
    || echo "$(date '+%F %T') No se pudo registrar el estado de la copia" >&2
}

# Sin una copia de las últimas 24 horas hay que crearla ya: el equipo puede apagarse antes de la hora programada
copia_vencida() {
  ultima="$(ls -1t "$CARPETA"/clinica_auto_*.dump 2>/dev/null | head -n 1)"
  [ -z "$ultima" ] || [ -n "$(find "$ultima" -mmin +1440)" ]
}

crear_copia() {
  archivo="$CARPETA/clinica_auto_$(date +%Y%m%d_%H%M%S).dump"
  if pg_dump -U "$POSTGRES_USER" --format=custom --file="$archivo.parcial" "$POSTGRES_DB" \
    && pg_restore --list "$archivo.parcial" > /dev/null \
    && mv "$archivo.parcial" "$archivo"; then
    echo "$(date '+%F %T') Copia creada y comprobada: $archivo"
    registrar_estado "ultima_exitosa"
    return 0
  fi
  rm -f "$archivo.parcial"
  echo "$(date '+%F %T') ERROR: la copia de seguridad falló; se reintentará en unos minutos" >&2
  registrar_estado "ultimo_error_en"
  return 1
}

depurar() {
  ls -1t "$CARPETA"/clinica_auto_*.dump 2>/dev/null | tail -n +"$((CONSERVAR + 1))" | xargs -r rm -f
}

echo "Copias automáticas activas: cada día desde las $HORA:00 ($TZ), se conservan $CONSERVAR"
while true; do
  hoy="$(date +%Y%m%d)"
  hora_actual="$(date +%H | sed 's/^0//')"
  if ! ls "$CARPETA"/clinica_auto_"$hoy"_*.dump > /dev/null 2>&1 && { [ "${hora_actual:-0}" -ge "$HORA" ] || copia_vencida; }; then
    crear_copia && depurar
  fi
  sleep 300
done
