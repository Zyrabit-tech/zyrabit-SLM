# Browser session

The web UI does not receive `ZYRABIT_API_KEY_WEB`.

On a new browser, the workspace asks for a key from `zyrabit-slm/.env`. `POST /v1/session` checks that key and sets two cookies:

| Cookie | Flags | Role |
| :--- | :--- | :--- |
| `zyrabit_session` | `HttpOnly`, `Path=/`, `SameSite` from `ZYRABIT_COOKIE_SAMESITE` (default `Lax`) | Server-side session id |
| `zyrabit_csrf` | readable by the page, same `SameSite` and `Secure` policy | Sent as `X-CSRF-Token` on POST, PUT, PATCH, and DELETE |

`Secure` is set when `ZYRABIT_COOKIE_SECURE=true` or the request is HTTPS. Behind HTTPS, set `ZYRABIT_COOKIE_SECURE=true` and `ZYRABIT_COOKIE_SAMESITE=strict`. `SameSite=None` is ignored unless `Secure` is also on.

The session expires after `ZYRABIT_SESSION_TTL_SECONDS` (default 43200). `DELETE /v1/session` ends it. CLI and service clients keep using `Authorization: Bearer`.

Existing installs that stored `zyrabit_api_token` in `localStorage` lose that copy on the next page load. Sign in once with the key from `.env`. Deleting documents still requires `ZYRABIT_API_KEY_ADMIN`.

`/runtime-config.js` is an empty object. It is not a place to put a credential.
