#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
OUT_DIR="${DOCGEN_TLS_OUT_DIR:-$(pwd)/build/tls_csr}"
COUNTRY="${DOCGEN_TLS_COUNTRY:-CN}"
STATE="${DOCGEN_TLS_STATE:-Shanghai}"
LOCALITY="${DOCGEN_TLS_LOCALITY:-Shanghai}"
ORG="${DOCGEN_TLS_ORG:-DocGen}"
ORG_UNIT="${DOCGEN_TLS_ORG_UNIT:-Operations}"
EMAIL="${DOCGEN_TLS_EMAIL:-}"
SANS_RAW="${DOCGEN_TLS_SANS:-}"

if [[ -z "$DOMAIN" ]]; then
  echo "[ERROR] usage: $0 <full-domain>" >&2
  echo "        example: $0 doc.niyoufei.com" >&2
  exit 1
fi

mkdir -p "$OUT_DIR/$DOMAIN"

DOMAIN_DIR="$OUT_DIR/$DOMAIN"
KEY_PATH="$DOMAIN_DIR/${DOMAIN}.key"
CSR_PATH="$DOMAIN_DIR/${DOMAIN}.csr"
CONF_PATH="$DOMAIN_DIR/${DOMAIN}.openssl.cnf"

if [[ -z "$SANS_RAW" ]]; then
  SANS_RAW="$DOMAIN"
fi

IFS=',' read -r -a SANS <<< "$SANS_RAW"

cat > "$CONF_PATH" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C = ${COUNTRY}
ST = ${STATE}
L = ${LOCALITY}
O = ${ORG}
OU = ${ORG_UNIT}
CN = ${DOMAIN}
EOF

if [[ -n "$EMAIL" ]]; then
  cat >> "$CONF_PATH" <<EOF
emailAddress = ${EMAIL}
EOF
fi

cat >> "$CONF_PATH" <<'EOF'

[req_ext]
subjectAltName = @alt_names

[alt_names]
EOF

idx=1
for san in "${SANS[@]}"; do
  san="$(printf '%s' "$san" | xargs)"
  if [[ -z "$san" ]]; then
    continue
  fi
  printf 'DNS.%s = %s\n' "$idx" "$san" >> "$CONF_PATH"
  idx=$((idx + 1))
done

if ! command -v openssl >/dev/null 2>&1; then
  echo "[ERROR] openssl not found" >&2
  exit 1
fi

if [[ -f "$KEY_PATH" || -f "$CSR_PATH" ]]; then
  echo "[ERROR] target files already exist in ${DOMAIN_DIR}" >&2
  echo "        remove them first or set DOCGEN_TLS_OUT_DIR to a new path" >&2
  exit 1
fi

openssl req -new -newkey rsa:2048 -nodes \
  -keyout "$KEY_PATH" \
  -out "$CSR_PATH" \
  -config "$CONF_PATH"

chmod 600 "$KEY_PATH"

echo "[OK] csr generated"
echo "     key: ${KEY_PATH}"
echo "     csr: ${CSR_PATH}"
echo "     openssl config: ${CONF_PATH}"
echo
echo "Next steps:"
echo "  1. Use the CSR with Let's Encrypt, your CA, or Cloudflare Origin CA."
echo "  2. Install the issued certificate on the origin host."
echo "  3. Export DOCGEN_SSL_CERT and DOCGEN_SSL_KEY, then rerun the domain bundle packaging."
