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

# Use psql to update the admin user's password using pgcrypto's crypt function
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<SQL
UPDATE public.users
SET password_hash = crypt('${NEW_PASSWORD}', gen_salt('bf')),
    is_active = TRUE
WHERE email = '${ADMIN_EMAIL}';

-- If no rows were updated, create the admin user with the provided password
INSERT INTO public.users (email, password_hash, full_name, is_active, is_superuser)
SELECT '${ADMIN_EMAIL}', crypt('${NEW_PASSWORD}', gen_salt('bf')), 'Administrator', TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM public.users WHERE email = '${ADMIN_EMAIL}');

SQL

echo "Admin password set for ${ADMIN_EMAIL}"
