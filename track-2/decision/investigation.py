from __future__ import annotations

import asyncio
from pathlib import Path

from api.main import DEFAULT_PRICE_BOOK
from decision.audit_storage import audit_lock, load_audit, save_audit
from decision.contracts import Investigation, NodeAudit, ToolCallRecord
from decision.data import load_snapshot
from decision.mcp_client import McpSession

IID, RID = "node_recommendation_audit", "rec_drain_nodes"


def not_run_investigation(dataset_id):
    return Investigation(investigation_id=IID, dataset_id=dataset_id, status="not_run",
        verdict="cannot_determine", evidence_origin="real_telemetry", recommendation_id=RID,
        finding_ids=[], summary="The MCP investigation has not run.",
        limitations=["No MCP evidence is available."], nodes=[], nominal_drain_gpu_hours_24h=0,
        tool_calls=[], model_used=None, token_usage=None)


def failed_investigation(dataset_id, receipt: ToolCallRecord, prior_calls=None):
    calls = list(prior_calls or [])
    if not calls or calls[-1].call_id != receipt.call_id: calls.append(receipt)
    return Investigation(investigation_id=IID, dataset_id=dataset_id, status="failed",
        verdict="cannot_determine", evidence_origin="real_telemetry", recommendation_id=RID,
        finding_ids=[], summary="The MCP investigation failed before evidence could be evaluated.",
        limitations=[f"{receipt.tool_name}: {receipt.error or receipt.status}"], nodes=[],
        nominal_drain_gpu_hours_24h=0, tool_calls=calls, model_used=None, token_usage=None)


def _chains(result):
    value = result.get("findings") if isinstance(result, dict) else None
    return value if isinstance(value, list) else []


def decide_node(*, node_name, resource_id, findings, causal_results, reported_findings,
                returned_findings, truncated, scope_description, corroboration):
    chains = [x for result in causal_results for x in _chains(result)]
    ids = sorted({str(f["id"]) for f in findings if f.get("id") is not None})
    if truncated or not chains:
        cause, verdict = "cannot_determine", "cannot_determine"
        reason = ("Finding pages were truncated." if truncated else
                  "Causal returned no chain; absence of a chain is not evidence of health.")
    else:
        culprits = [c for chain in chains for c in chain.get("culprit") or []]
        types = {c.get("type") for c in culprits}
        roots = {str(c.get("resource_id")) for c in culprits}
        patterns = {h.get("pattern") for c in chains for h in c.get("causal_chain") or []}
        synthetic = any(f.get("metadata", {}).get("synthetic") for f in findings)
        if synthetic or "k8s:volume" in types:
            cause, verdict, reason = "cannot_determine", "no_drain", "Synthetic/shared-volume evidence cannot support a real hardware conclusion."
        elif {"k8s:namespace", "k8s:job"} & types or {"concentrated_in_one_person", "uniform_failure"} & patterns:
            cause, verdict, reason = "user_code", "no_drain", "The bounded chain attributes this episode to a user or array workload."
        elif resource_id in roots and "k8s:node" in types and corroboration and corroboration.get("users", 0) > 1:
            cause, verdict, reason = "hardware", "inspect", "A node-rooted chain has multi-user corroboration; inspect before draining."
        elif corroboration:
            cause, verdict, reason = "workload_mix", "no_drain", "Observed exposure does not establish a hardware cause."
        else:
            cause, verdict, reason = "cannot_determine", "cannot_determine", "The chain lacks local corroboration."
    if corroboration: reason += f" Denominator: {corroboration['jobs']} explicitly linked jobs, {corroboration['users']} users."
    return NodeAudit(node_name=node_name, resource_id=resource_id, cause=cause, verdict=verdict,
        scope_description=scope_description, finding_ids=ids, reported_findings=reported_findings,
        returned_findings=returned_findings, truncated=truncated, reasoning=reason)


def _corroborate(snapshot, findings):
    ids = {str(f.get("metadata", {}).get("job_id")) for f in findings if f.get("metadata", {}).get("job_id") is not None}
    jobs = snapshot.jobs[snapshot.jobs.id_job.astype(str).isin(ids)]
    return {"jobs": len(jobs), "users": int(jobs.id_user.dropna().nunique()) if "id_user" in jobs else 0}


async def run_investigation(
    data_dir: Path, output_dir: Path, *, snapshot=None
):
    snap = snapshot
    if snap is None:
        snap = await asyncio.to_thread(load_snapshot, Path(data_dir))
    cached = await asyncio.to_thread(load_audit, output_dir, snap.dataset_id)
    if cached: return cached
    with audit_lock(output_dir, snap.dataset_id) as acquired:
        if not acquired:
            return not_run_investigation(snap.dataset_id).model_copy(update={"status": "running", "summary": "Another audit holds the dataset lock."})
        raw = Path(output_dir) / "mcp" / snap.dataset_id / "raw"
        async with McpSession(data_dir, total_timeout_sec=120, per_call_timeout_sec=20,
                              max_business_calls=25, raw_dir=raw) as session:
            if session.records[0].status != "success":
                result = failed_investigation(snap.dataset_id, session.records[0], session.records); save_audit(output_dir, result); return result
            price = float(DEFAULT_PRICE_BOOK.usd_per_gpu_hour)
            spec = [("health", {}), ("list_rules", {}), ("recommendations", {"usd_per_gpu_hour": price}),
                    ("underperforming", {"entity_type": "node", "limit": 5, "usd_per_gpu_hour": price})]
            base = [await session.call(*x) for x in spec]
            if any(x.status != "success" for x in base):
                bad = next(x for x in base if x.status != "success")
                result = failed_investigation(snap.dataset_id, bad, session.records); save_audit(output_dir, result); return result
            rec = next((x for x in base[2].result.get("recommendations", []) if x.get("id") == RID), None)
            if not rec:
                result = failed_investigation(snap.dataset_id, base[2], session.records).model_copy(update={"status": "partial", "summary": "rec_drain_nodes was absent."}); save_audit(output_dir, result); return result
            types = dict(zip(snap.resources.id.astype(str), snap.resources.type.astype(str)))
            nodes, seen = [], set()
            for row in base[3].result.get("rows", []):
                rid = str(row.get("resource_id", ""))
                if rid and rid not in seen and types.get(rid) == "k8s:node": seen.add(rid); nodes.append((str(row.get("entity_id", rid)), rid))
                if len(nodes) == 5: break
            found, totals, cuts = {}, {}, {}
            for _, rid in nodes:
                first = await session.call("list_findings", {"resource_id": rid, "limit": 100, "offset": 0})
                values = list(first.result.get("findings", [])) if first.status == "success" else []
                total = int(first.result.get("total", len(values))) if first.result else 0
                if total > 100 and session._business_calls < 14:
                    second = await session.call("list_findings", {"resource_id": rid, "limit": 100, "offset": 100})
                    if second.status == "success": values += second.result.get("findings", [])
                dedup = {str(x.get("id")): x for x in values if x.get("id") is not None}
                found[rid], totals[rid], cuts[rid] = list(dedup.values()), total, len(dedup) < total
            ranked, empty = [], None
            for _, rid in nodes:
                for f in found[rid]:
                    detector = str(f.get("detectorId", "")); ranked.append(((0 if "hardware" in detector else 1 if f.get("rootCauses") else 3, str(f["id"])), rid, f))
                    if not f.get("rootCauses") and empty is None: empty = (rid, f)
            chosen = [empty] if empty else []
            for _, rid, f in sorted(ranked):
                if (rid, f) not in chosen: chosen.append((rid, f))
                if len(chosen) == 8: break
            causal = {rid: [] for _, rid in nodes}; neighbors = []
            for rid, f in chosen:
                call = await session.call("causal", {"finding_id": str(f["id"]), "hop_count": 3})
                if call.status == "success":
                    causal[rid].append(call.result)
                    for chain in _chains(call.result):
                        for culprit in chain.get("culprit") or []:
                            value = str(culprit.get("resource_id", ""))
                            if value and value not in neighbors: neighbors.append(value)
            for rid in neighbors[:3]: await session.call("neighbor", {"resource_ids": [rid], "hop_count": 1})
            scope = f"Mapped sample {snap.sample_window.mapped_start_utc} to {snap.sample_window.mapped_end_utc}; episode-only conclusion."
            audits = [decide_node(node_name=name, resource_id=rid, findings=found[rid], causal_results=causal[rid], reported_findings=totals[rid], returned_findings=len(found[rid]), truncated=cuts[rid], scope_description=scope, corroboration=_corroborate(snap, found[rid])) for name, rid in nodes]
            partial = any(x.status != "success" for x in session.records) or any(x.truncated for x in audits)
            flags = {bool(f.get("metadata", {}).get("synthetic")) for fs in found.values() for f in fs}
            origin = "mixed" if len(flags) > 1 else ("synthetic_incident" if flags == {True} else "real_telemetry")
            result = Investigation(investigation_id=IID, dataset_id=snap.dataset_id, status="partial" if partial else "completed",
                verdict="revise" if audits else "cannot_determine", evidence_origin=origin, recommendation_id=RID,
                finding_ids=sorted({i for x in audits for i in x.finding_ids}),
                summary="Replace finding-count-based automatic drain with bounded causal diagnosis.",
                limitations=["Bounded to 25 business calls; not a fleet-wide reliability study."] + (["At least one call/page was incomplete."] if partial else []),
                nodes=audits, nominal_drain_gpu_hours_24h=len(nodes) * 48, tool_calls=session.records,
                model_used=None, token_usage=None)
            save_audit(output_dir, result); return result


def load_investigation(output_dir, dataset_id):
    return load_audit(output_dir, dataset_id)
