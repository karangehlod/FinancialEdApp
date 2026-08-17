#!/usr/bin/env bash
# One-off admin password setter. Usage:
#   ./scripts/set_admin_password.sh postgres://user:pass@localhost:55432/auth_db admin@example.com 'new-password'

set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <DATABASE_URL> <ADMIN_EMAIL> <NEW_PASSWORD>"
  exit 2
fi

DATABASE_URL="$1"
ADMIN_EMAIL="$2"
NEW_PASSWORD="$3"

# Escape single quotes for SQL string literals (double them per the SQL standard).
# This prevents SQL injection from user-supplied values.
safe_quote() {
  printf "%s" "$1" | sed "s/'/''/g"
}

SAFE_EMAIL=$(safe_quote "$ADMIN_EMAIL")
SAFE_PASSWORD=$(safe_quote "$NEW_PASSWORD")

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<SQL
UPDATE public.users
SET password_hash = crypt('${SAFE_PASSWORD}', gen_salt('bf')),
    is_active = TRUE
WHERE email = '${SAFE_EMAIL}';

INSERT INTO public.users (email, password_hash, full_name, is_active, is_superuser)
SELECT '${SAFE_EMAIL}', crypt('${SAFE_PASSWORD}', gen_salt('bf')), 'Administrator', TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM public.users WHERE email = '${SAFE_EMAIL}');
SQL

echo "Admin password set for ${ADMIN_EMAIL}"
