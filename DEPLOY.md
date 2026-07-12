# Deploying (Railway, Render, Fly — anything that reads a Procfile)

The app is started by the **Procfile**, which runs gunicorn:

    web: gunicorn "app:app" --bind 0.0.0.0:$PORT ...

Never let the platform run `python app.py` instead. That starts Flask's
development server, which binds localhost (so the platform cannot route traffic
to it) and — worse — serves the Werkzeug interactive debugger, which executes
arbitrary Python typed into the browser. The debugger PIN is not protection.

`$PORT` is supplied by the platform. Do not hard-code it.

---

## Environment variables to set on the host

Set these in the platform's dashboard (Railway: Variables). They are the same
keys as `.env`, which is **never** committed.

| Variable | Value | Why |
|---|---|---|
| `VERDA_ENV` | `production` | Turns on Secure cookies and HSTS, and makes the app refuse to boot on a default secret key. |
| `SECRET_KEY` | 64 random hex chars | Signs the session cookie. **Generate a fresh one — do not reuse the development key.** `python -c "import secrets; print(secrets.token_hex(32))"` |
| `MONGO_URI` | the Atlas driver string | The database. |
| `MONGO_DB` | `verda` | |
| `TRUST_PROXY` | `1` | Railway terminates TLS in front of the app. Without this every visitor appears to come from the proxy's IP, so the login rate limiter would treat them as one person and lock everybody out together. |
| `ADMIN_USERNAME` | your staff username | Not `admin` — the seeder refuses guessable names. |
| `ADMIN_PASSWORD` | a long random password | Only read when the account is first created. |
| `ADMIN_FIRST_NAME` / `ADMIN_LAST_NAME` | display name | Shown in the admin sidebar. |
| `CLOUDINARY_CLOUD_NAME` | | Product and hero images. Without these the app still runs; only uploads are disabled. |
| `CLOUDINARY_API_KEY` | | |
| `CLOUDINARY_API_SECRET` | | Treat as a password. |
| `MAX_UPLOAD_MB` | `6` | Largest product image accepted. |

## Atlas network access

Atlas rejects connections from unknown addresses. The platform's outbound IP is
not fixed, so either allow `0.0.0.0/0` in **Atlas → Network Access** (the
database is still protected by its username and password) or use the platform's
static-egress feature if it has one, and allow just that address.

If the app boots but every page 500s on the database, this is almost always why.

## First deploy: seed the data

Once the service is up, run these **once** from the platform's shell
(Railway: the service's "Command" / shell tab):

    flask seed-products     # loads the starting catalogue
    flask seed-admin        # creates the superadmin from ADMIN_USERNAME/PASSWORD

Both are safe to re-run: they will not duplicate products or overwrite a
password that has since been changed.

## Checks after deploying

    curl -sI https://<your-app>/ | grep -i "content-security-policy\|strict-transport"

Expect a CSP and an HSTS header. If HSTS is missing, `VERDA_ENV` is not
`production`.
