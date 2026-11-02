# OpenViking v0.4.22

## 中文

### 亮点

- 运行时配置与 Account 隔离：新增 Cluster / Account 两级运行时配置（`GET/PATCH /api/v1/admin/configuration`、`/api/v1/admin/accounts/{account_id}/configuration`），无需改 `ov.conf` 或重启；Account 可独立配置 VLM、Query Planner、Embedding、远端 VectorDB 和 Feishu 应用凭证；新增部署级 `server.user_config_defaults.auto_commit_policy`；未知配置字段改为忽略并输出 WARNING。
- Skill 检索与分发：Skill 整包参与索引，`skills/find` 与 `search(mode="context")` 每个 Skill 只返回一条最佳命中；MCP 新增 `add_skill` 工具；各 memory 插件在会话开始注入 Skill 目录并附带 `openviking-skills` skill。
- 检索与存储：本地向量引擎 cosine 分数归一化到 `[0,1]`；新增 openGauss DataVec 向量后端和 Jev rerank provider；grep 支持匹配行上下文，fallback 目录遍历分页，canonical session 使用原生扫描；增量资源导入优化；统一存储 URI 规范化，兼容中文与含空格路径；tags 新增 `tag_mode="clear"`；修复写入等待遗漏下游索引任务、语义目录锁冲突重排队、mkdir 摘要并发创建。
- ACL 与 Studio：开启 ACL 后共享根默认 `user:* = manage` 并继承，`add_resource` / `mkdir` / `write` 支持创建时传 `acl`；Studio 新增资源权限管理、用户组管理、Mermaid 预览、Account 列表大小写不敏感搜索（`?query=`）。
- Agent 插件：OpenCode 插件支持 OpenCode v2；新增 Kimi Code CLI memory 插件；pi 扩展改用服务端 MCP 工具集；Hermes 新增 gateway 记忆预设和发送者归属；MCP `list` 默认 `viking://`，`edit` 提示 CRLF/LF 不匹配。
- 可观测性与解析：新增 QueueFS 处理耗时、asyncio executor 指标；observer API 支持 `?format=json`；新增飞书思维笔记解析；Git Watch 认证失败自动停用；Watch 任务支持外部 OAuth token 管理。
- 安全：镜像不再内置 ripgrep，RAGFS 不再探测或调用外部 `rg` 命令。

### 兼容性与迁移

1. **Session `used` 上报接口移除（#5252）**：删除 `POST /api/v1/sessions/{session_id}/used`、Python `Session.used()`、Studio `/session used` 命令和生成客户端中的对应方法。调用该接口返回 404。`contexts_used` / `skills_used` 统计从 session 指标和存储统计中移除，`active_count` 保留。依赖该接口的调用方直接删除调用。

   ```bash
   # 修改前：200；修改后：404
   curl -X POST "$OV_URL/api/v1/sessions/$SID/used" -H "X-API-Key: $KEY" \
     -H 'Content-Type: application/json' -d '{"contexts":["viking://resources/a.md"]}'
   ```

2. **记忆抽取解析失败时 session commit 任务失败（#5171）**：修改前，模型在重试耗尽后仍返回无法解析的抽取结果时，commit 任务报告成功且记忆数为 0。修改后，任务与 archive 标记为 `failed`，错误信息包含 `failure_kind=parse_error`（空响应为 `failure_kind=empty_response`）。模型确认无变更时返回 `sdk.commit()`，仍按成功完成。按任务状态做告警或重试的调用方需要处理新的 `failed` 结果。

3. **运行时配置系统（#5140、#5323）**：
   - 以下接口保留但标记为 deprecated，新客户端迁移到 configuration API：`GET/PATCH /api/v1/admin/accounts/{account_id}/settings`、`GET/PUT /api/v1/admin/agent-evolution`。
   - Account 配置仍写入 `/local/{account_id}/_system/setting.json`。旧版本副本遇到新字段可能无法解析该文件，新旧副本共享存储滚动升级期间不要写入旧版本不识别的 Account 配置字段。
   - Account 的 `vlm`、`query_planner`、`embedding`、`vectordb` 仅 ROOT 可管理；ADMIN 读取时脱敏，写入返回 `403 PERMISSION_DENIED`。未配置这些字段的既有 Account 继续使用 Cluster 默认配置。
   - Account 的 Embedding / VectorDB 属于创建期配置；模型、维度或 VectorDB 变更不会自动重建历史向量，需要调用方执行 Reindex。

   ```bash
   curl -X PATCH "$OV_URL/api/v1/admin/accounts/acme/configuration" \
     -H "X-API-Key: $ROOT_KEY" -H 'Content-Type: application/json' \
     -d '{"acl": {"enabled": true}}'   # 字段缺失=不改，值=设置，null=删除当前层覆盖
   ```

4. **未知配置字段不再阻止启动（#5165、#5193）**：`ov.conf` 与 Account `setting.json` 中的未知字段改为忽略，并输出 `Ignoring unknown config field '<path>'` WARNING（不输出值）。已知字段的类型错误仍报错。拼写错误的字段也会被忽略，升级后检查启动日志中的该 WARNING。遗留的 `namespace` 隔离配置会被忽略且不生效。

5. **ACL 默认权限（#5266）**：仅影响开启 `acl.enabled` 的 Account（开关默认关闭）。

   | 场景 | 修改前 | 修改后 |
   | --- | --- | --- |
   | Alice 在默认共享目录创建 `a.md` | Alice 获得直接 manage，Bob 不能管理 | 无直接权限，继承 `user:* = manage`，Bob 可以管理 |
   | Alice 只有 restricted 父目录的 write，创建时不传 ACL | 创建者额外获得 manage | 只继承 write，不能修改 ACL |
   | 创建或导入时传 `acl` | 不支持 | 先检查 manage，只有 write 返回 403 |

   需要限制访问的目录应显式设置 `restricted`：

   ```bash
   curl -X POST "$OV_URL/api/v1/fs/mkdir" -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
     -d '{"uri":"viking://resources/project-a","acl":{"acl_mode":"restricted","entries":[{"principal":"user:alice","level":"manage"},{"principal":"group:dev","level":"read"}]}}'
   ```

   CLI 使用 `--acl`，Python / Go / TypeScript SDK 同步支持。

6. **本地向量引擎 cosine 分数范围（#5358）**：native C++ 与 cuVS 的纯 cosine 分数由 `[-1,1]` 映射为 `(cos + 1) / 2`，范围 `[0,1]`，排序不变（例：原始 0 → 0.5，-0.6 → 0.2）。IP、L2、稀疏融合分数不变，阈值数值不自动调整。对 cosine 分数设置了 `score_threshold` 或按分数过滤的调用方需要重新校准阈值。旧索引无需重建；降级后恢复原始分数。

7. **Skill 检索结果（#5045、#5255）**：`skills/find` 每个 Skill 返回包内得分最高的一条，`uri` 可能指向 L0、L1 或包内文件。依赖 `uri` 取包根目录的代码改用 `root_uri`。升级不自动重建旧 Skill；为旧 Skill 补齐整包摘要和索引需执行 `semantic_and_vectors` 模式的 reindex（`vectors_only` 不生成缺失摘要）。

   ```bash
   ov reindex viking://agent/skills --mode semantic_and_vectors
   ```

8. **目录导入文件数默认不限制（#5231、#5242）**：`parsers.directory.max_files` 默认值由 `1000` 改为 `null`（不限制）。需要保留上限时显式配置：

   ```json
   { "parsers": { "directory": { "max_files": 1000 } } }
   ```

9. **保留名规则（#5170）**：账号根以下用户创建的 `tasks` / `_system` 目录现在出现在 `ls` / `tree` / `glob` 结果中。对 `.redirect.json`、`.sync_log.json`、`.exact.ovlock.*`（及 replace 模式写 `.path.ovlock`）执行 `write` / `mkdir` / `cp` / `mv` 返回 `INVALID_ARGUMENT`；WebDAV 对 `.exact.ovlock.*` 返回 404。

10. **pi 扩展 0.4.0（#5272）**：7 个手写 `viking_*` 工具替换为服务端 MCP 工具集，注册为 `openviking_<tool>`。Root API key 不能访问 `/mcp`，需使用 user 或 admin key。迁移说明见扩展 README。

11. **OpenClaw peer role（#5355）**：安装时 `--peer-role person`、`OPENVIKING_PEER_ROLE=person` 和交互式输入 `person` 会报错并提示改用 `sender`。已有配置中的 `peer_role: "person"` 继续按 `sender` 处理。

12. **VikingBot OpenSandbox（#5269）**：`bot.sandbox.backend=opensandbox` 时默认 `managed=true`，由 Gateway / `--with-bot` 托管 Docker OpenSandbox。已有外部 OpenSandbox 服务需显式设置 `bot.sandbox.backends.opensandbox.managed=false`。新工作目录不自动迁移旧 `bot/workspace/shared` 的文件。默认 `direct` 行为不变。

## English

### Highlights

- Runtime configuration and account isolation: adds Cluster / Account runtime configuration (`GET/PATCH /api/v1/admin/configuration`, `/api/v1/admin/accounts/{account_id}/configuration`) without editing `ov.conf` or restarting. Accounts can have their own VLM, Query Planner, Embedding, remote VectorDB, and Feishu app credentials. Adds deployment-level `server.user_config_defaults.auto_commit_policy`. Unknown config fields are now ignored with a WARNING.
- Skill retrieval and distribution: whole Skill packages are indexed; `skills/find` and `search(mode="context")` return one best hit per Skill. MCP adds an `add_skill` tool; the memory plugins inject a Skill catalog at session start and ship an `openviking-skills` skill.
- Retrieval and storage: local vector engine cosine scores are normalized to `[0,1]`; adds an openGauss DataVec vector backend and a Jev rerank provider; grep supports context lines, paginates fallback directory traversal, and uses a native scanner for canonical sessions; incremental resource ingestion is faster; storage URI normalization handles Unicode and space-containing paths; tags add `tag_mode="clear"`; fixes write waits missing downstream index tasks, requeues semantic directory lock conflicts, and serializes mkdir abstract creation.
- ACL and Studio: with ACL enabled, the shared root defaults to inherited `user:* = manage`; `add_resource` / `mkdir` / `write` accept `acl` at creation. Studio adds resource permission management, user group management, Mermaid previews, and case-insensitive account search (`?query=`).
- Agent plugins: the OpenCode plugin supports OpenCode v2; adds a Kimi Code CLI memory plugin; the pi extension uses the server's MCP tool surface; Hermes adds gateway memory presets and sender attribution; MCP `list` defaults to `viking://` and `edit` reports CRLF/LF mismatches.
- Observability and parsing: adds QueueFS processing latency and asyncio executor metrics; observer API supports `?format=json`; adds Feishu mindnote parsing; Git watches deactivate on authentication failure; watch tasks support externally managed OAuth tokens.
- Security: the image no longer ships ripgrep, and RAGFS no longer probes or invokes an external `rg` binary.

### Compatibility and Migration

1. **Session `used` reporting API removed (#5252):** removes `POST /api/v1/sessions/{session_id}/used`, Python `Session.used()`, the Studio `/session used` command, and the matching generated client method. Calls return 404. `contexts_used` / `skills_used` are removed from session metrics and storage stats; `active_count` is kept. Callers should drop the call.

   ```bash
   # before: 200; after: 404
   curl -X POST "$OV_URL/api/v1/sessions/$SID/used" -H "X-API-Key: $KEY" \
     -H 'Content-Type: application/json' -d '{"contexts":["viking://resources/a.md"]}'
   ```

2. **Session commit fails on unparseable memory extraction (#5171):** before, when the model still returned unparseable extraction output after all retries, the commit task reported success with zero memories. Now the task and archive are marked `failed` and the error contains `failure_kind=parse_error` (`failure_kind=empty_response` for empty responses). A model that confirms no changes returns `sdk.commit()` and still completes successfully. Callers that alert or retry on task status need to handle the new `failed` outcome.

3. **Runtime configuration system (#5140, #5323):**
   - Still available but deprecated; new clients should use the configuration API: `GET/PATCH /api/v1/admin/accounts/{account_id}/settings`, `GET/PUT /api/v1/admin/agent-evolution`.
   - Account configuration is still written to `/local/{account_id}/_system/setting.json`. Older replicas may fail to parse it once new fields are written. During a rolling upgrade with shared storage, do not write account fields that the old version does not recognize.
   - Account `vlm`, `query_planner`, `embedding`, and `vectordb` are ROOT-only; ADMIN reads are redacted and writes return `403 PERMISSION_DENIED`. Existing accounts without these fields keep using the Cluster defaults.
   - Account Embedding / VectorDB are creation-time settings. Changing model, dimension, or VectorDB does not rebuild existing vectors; run a Reindex.

   ```bash
   curl -X PATCH "$OV_URL/api/v1/admin/accounts/acme/configuration" \
     -H "X-API-Key: $ROOT_KEY" -H 'Content-Type: application/json' \
     -d '{"acl": {"enabled": true}}'   # missing = unchanged, value = set, null = remove this layer's override
   ```

4. **Unknown config fields no longer block startup (#5165, #5193):** unknown fields in `ov.conf` and account `setting.json` are ignored and logged as `Ignoring unknown config field '<path>'` (values are not logged). Type errors in known fields still fail. Typos are ignored too, so check startup logs for this WARNING after upgrading. Legacy `namespace` isolation settings are ignored and have no effect.

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

6. **Local vector engine cosine score range (#5358):** native C++ and cuVS map pure cosine scores from `[-1,1]` to `(cos + 1) / 2` in `[0,1]`; ranking is unchanged (e.g. raw 0 → 0.5, -0.6 → 0.2). IP, L2, and sparse-fusion scores are unchanged, and thresholds are not adjusted automatically. Callers using `score_threshold` or score filters on cosine indexes should recalibrate. Existing indexes need no rebuild; a downgrade restores raw scores.

7. **Skill search results (#5045, #5255):** `skills/find` returns one best hit per Skill, and `uri` may point at L0, L1, or a file in the package. Code that used `uri` as the package root should use `root_uri`. Existing Skills are not reprocessed on upgrade; run a `semantic_and_vectors` reindex to build package-level summaries and indexes (`vectors_only` does not generate missing summaries).

   ```bash
   ov reindex viking://agent/skills --mode semantic_and_vectors
   ```

8. **Directory import file limit off by default (#5231, #5242):** `parsers.directory.max_files` defaults to `null` (unlimited) instead of `1000`. To keep a limit, set it explicitly:

   ```json
   { "parsers": { "directory": { "max_files": 1000 } } }
   ```

9. **Reserved names (#5170):** user-created `tasks` / `_system` directories below the account root now appear in `ls` / `tree` / `glob`. `write` / `mkdir` / `cp` / `mv` targeting `.redirect.json`, `.sync_log.json`, `.exact.ovlock.*` (and replace-mode writes to `.path.ovlock`) return `INVALID_ARGUMENT`; WebDAV returns 404 for `.exact.ovlock.*`.

10. **pi extension 0.4.0 (#5272):** the seven hand-written `viking_*` tools are replaced by the server's MCP tools, registered as `openviking_<tool>`. Root API keys cannot access `/mcp`; use a user or admin key. See the extension README for migration notes.

11. **OpenClaw peer role (#5355):** `--peer-role person`, `OPENVIKING_PEER_ROLE=person`, and entering `person` at the interactive prompt now fail with a hint to use `sender`. Existing `peer_role: "person"` in plugin config is still treated as `sender`.

12. **VikingBot OpenSandbox (#5269):** with `bot.sandbox.backend=opensandbox`, `managed=true` is the default and Gateway / `--with-bot` manages a Docker-backed OpenSandbox. Existing external OpenSandbox services must set `bot.sandbox.backends.opensandbox.managed=false`. Files in the old `bot/workspace/shared` are not migrated to the new workspace. The default `direct` backend is unchanged.

## First-time Contributors

- @blrain3 — https://github.com/volcengine/OpenViking/pull/5095
- @Jp121987 — https://github.com/volcengine/OpenViking/pull/5213
- @antoniopan — https://github.com/volcengine/OpenViking/pull/5225
- @auyua9 — https://github.com/volcengine/OpenViking/pull/5234
- @Syt3s — https://github.com/volcengine/OpenViking/pull/4319
- @cocolord — https://github.com/volcengine/OpenViking/pull/5270
- @AnnaSuSu — https://github.com/volcengine/OpenViking/pull/5308
- @wellkilo — https://github.com/volcengine/OpenViking/pull/5183
- @dvd233 — https://github.com/volcengine/OpenViking/pull/5318
- @ydflow — https://github.com/volcengine/OpenViking/pull/5312
- @ligjn — https://github.com/volcengine/OpenViking/pull/5149
- @HMYDK — https://github.com/volcengine/OpenViking/pull/5353

Full Changelog: https://github.com/volcengine/OpenViking/compare/v0.4.21...v0.4.22
