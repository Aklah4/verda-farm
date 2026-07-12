# Verda Farm

Flask + Jinja2 implementation of the **Verda Farm** design
(`Verda Farm.dc.html` from the Claude Design project).

The design was a single-page component that swapped views via client state. Here
each view is a real URL, the cart lives in the session, and every form is
validated server-side.

## Run

The project uses a virtual environment in `.venv/`.

```powershell
.\.venv\Scripts\Activate.ps1     # PowerShell  (cmd: .venv\Scripts\activate.bat)
python app.py                    # http://127.0.0.1:5000
```

To recreate it from scratch:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Layout

```
app.py            application factory — filters, context, error handlers
config.py         env-driven settings (accent, hero layout, WhatsApp, secret key)
data.py           product catalogue and static page content
cart_service.py   session cart: add / change_qty / remove / summary
routes/
  main.py         /            /about          /whatsapp
  shop.py         /shop        /product/<id>
  cart.py         /cart        /cart/add|update|remove   /checkout
                  /order/confirmation           /quote
  leads.py        /contact     /wholesale      /export
  auth/           /login       /logout
    session.py    owns the session keys that say who is signed in
  dashboard/      /dashboard   /dashboard/preferences
    service.py    orders, headline figures, saved preferences
templates/        base layout + one template per page
  auth/login.html        sign-in page
  dashboard/index.html   signed-in dashboard
  partials/macros.html   ProductCard component + form-field macros
static/css, static/js
```

## Notes

- **Prices** are integer naira, formatted by the `naira` Jinja filter.
- **Cart** is a session list of `{id, qty}`; delivery is a flat ₦3,500 once the
  cart is non-empty, and a single line is capped at `MAX_LINE_QTY` (999). Every
  mutation is POST-then-redirect, so a refresh never re-submits.
- **Auth is a stub.** `routes/auth/` signs in anyone who supplies an email and a
  password, exactly as the prototype did. Replace the check in `auth/routes.py`
  before this goes near production. Nothing outside that package touches the
  session keys directly — the rest of the app goes through `auth/session.py`
  (`start_session`, `is_logged_in`, `login_required`), so that swap stays local.
- **Dashboard** (`routes/dashboard/`) is behind `login_required`. Order history
  is the sample data plus whatever was ordered this session, and preferences are
  stored in the session — both move to a user table once one exists.
- **Checkout takes card fields but processes no payment** — it is the design's
  prototype checkout. Wire it to a real processor (and stop accepting raw card
  numbers into your own form) before taking money.

## Security

- **CSRF** — `CSRFProtect` is on for every POST; each form carries a
  `csrf_token` hidden input. A form without one gets a 400.
- **Redirects** — `next` params and the `Referer` header are attacker-controlled,
  so `security.py` proves a target is same-origin before it reaches `redirect()`.
  Anything off-site falls back to a known endpoint.
- **`SECRET_KEY`** — loaded from `.env` (gitignored). With `VERDA_ENV=production`
  the app *refuses to boot* on the development default, since a known key means
  forgeable sessions. Generate one with:
  `python -c "import secrets; print(secrets.token_hex(32))"`

## Environment

Copy `.env.example` to `.env`. Real environment variables override the file.

| Variable | Default | Effect |
|---|---|---|
| `SECRET_KEY` | dev default | Session signing key. Required in production. |
| `VERDA_ENV` | `development` | `production` enforces a real `SECRET_KEY` |
| `VERDA_ACCENT` | `#2E7D4E` | Accent colour |
| `VERDA_HERO` | `split` | `split` or `centered` homepage hero |
| `VERDA_WHATSAPP` | `1` | `0` hides the floating WhatsApp button |
