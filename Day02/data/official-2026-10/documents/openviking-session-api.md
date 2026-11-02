1. **Session `used` reporting API removed (#5252):** removes `POST /api/v1/sessions/{session_id}/used`, Python `Session.used()`, the Studio `/session used` command, and the matching generated client method. Calls return 404. `contexts_used` / `skills_used` are removed from session metrics and storage stats; `active_count` is kept. Callers should drop the call.

   ```bash
   # before: 200; after: 404
   curl -X POST "$OV_URL/api/v1/sessions/$SID/used" -H "X-API-Key: $KEY" \
     -H 'Content-Type: application/json' -d '{"contexts":["viking://resources/a.md"]}'
   ```

