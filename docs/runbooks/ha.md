# HA & disaster-recovery runbook (F12)

This runbook documents how the JumlaOS API and worker tiers stay
available during single-region or single-machine failures, and the
procedures the on-call engineer follows to recover.

## Topology

| Tier   | Primary region | Failover region | Min machines | Max machines |
|--------|----------------|-----------------|--------------|--------------|
| API    | `cdg` (Paris)  | `ams` (Amsterdam) | 2            | 4            |
| Worker | `cdg`          | `ams`           | 2            | 4            |
| Postgres | `cdg`        | `ams` (replica) | 1 primary + 1 replica | n/a |
| Redis  | `cdg`          | `ams` (read replica) | 1 primary + 1 replica | n/a |

* `auto_stop_machines = "stop"` — Fly tears the machine down on idle and
  brings up a fresh one on demand. ``suspend`` is *not* used in prod
  because a process that's hung at suspend stays hung at resume.
* `min_machines_running = 2` — at least two API machines per app, so a
  single VM dying does not cause downtime.
* `[[scaling]] min/max_machines = 2/4` — Fly scales between two and four
  machines per app per region based on concurrency limits.
* Worker has an `exec` health check that grep's the entrypoint process;
  Fly replaces the machine if the check fails three times in a row.

## RTO / RPO targets

| Scenario | RTO | RPO |
|----------|-----|-----|
| Single API machine dies | 0 (the other machine serves immediately) | 0 |
| Single worker machine dies | < 30 s (next health check kicks in) | 0 |
| Region `cdg` outage | < 5 min (manual failover via `flyctl regions set`) | < 1 min (Postgres physical replication lag) |
| Postgres primary loss | < 10 min (promote replica) | < 5 min |
| Redis primary loss | < 1 min (rate-limit + idempotency degrade gracefully) | n/a (cache only) |

## Failover drills

Run a region-failure drill every quarter. The "drill" steps:

1. Notify on-call (`#oncall`) and product (`#product`) channels.
2. Pre-flight checks:
   ```sh
   flyctl status --app jumlaos-api
   flyctl status --app jumlaos-worker
   flyctl ssh console --app jumlaos-api -C "curl -fsS localhost:8080/v1/readyz"
   ```
3. Drain the primary region:
   ```sh
   flyctl regions remove cdg --app jumlaos-api
   flyctl regions remove cdg --app jumlaos-worker
   ```
4. Verify all traffic is served from `ams`:
   ```sh
   flyctl logs --app jumlaos-api | grep -i ams
   ```
5. Restore primary region and re-balance:
   ```sh
   flyctl regions add cdg --app jumlaos-api
   flyctl regions add cdg --app jumlaos-worker
   flyctl scale count 2 --region cdg --app jumlaos-api
   flyctl scale count 2 --region cdg --app jumlaos-worker
   ```
6. Postmortem: file a doc in `docs/postmortems/YYYY-MM-DD-ha-drill.md`
   capturing actual RTO and any deviations.

## Production scale-out

```sh
flyctl scale count 2 --region cdg,ams --app jumlaos-api
flyctl scale count 2 --region cdg,ams --app jumlaos-worker
```

## Health-check endpoints

* `/v1/livez` — process up, event loop responsive. Used by Fly's
  liveness probe.
* `/v1/readyz` — DB + Redis + Procrastinate jobs table + R2 reachable
  within 500 ms each. Used by Fly's HTTP service check and load balancer.
