5. **ACL default permissions (#5266):** applies only to accounts with `acl.enabled` (off by default).

   | Scenario | Before | After |
   | --- | --- | --- |
   | Alice creates `a.md` in the default shared directory | Alice gets direct manage; Bob cannot manage | No direct entry; inherits `user:* = manage`; Bob can manage |
   | Alice has only write on a restricted parent, creates without ACL | Creator gets extra manage | Inherits write only; cannot change ACL |
   | `acl` passed on create/import | Not supported | Requires manage; write-only callers get 403 |

   Set `restricted` explicitly on directories that need limited access:

   ```bash
   curl -X POST "$OV_URL/api/v1/fs/mkdir" -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
     -d '{"uri":"viking://resources/project-a","acl":{"acl_mode":"restricted","entries":[{"principal":"user:alice","level":"manage"},{"principal":"group:dev","level":"read"}]}}'
   ```

   The CLI uses `--acl`; the Python, Go, and TypeScript SDKs support the same field.

