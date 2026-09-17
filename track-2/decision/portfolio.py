from dataclasses import dataclass
from decision.contracts import ActionId

@dataclass(frozen=True)
class Allocation:
    owner_by_job: dict[str, ActionId]
    overlap_jobs: int

def allocate_candidates(ledger, selected_action_ids):
    selected = set(selected_action_ids)
    eligible = ledger.rows[ledger.rows.eligible]
    sets = {action: set(eligible.loc[eligible.action_id == action, "job_id"]) for action in selected}
    owners = {}
    for action in ("cpu_migration", "idle_session_reclaim"):
        if action in selected:
            for job_id in sets[action]: owners.setdefault(job_id, action)
    overlap = len(sets.get("cpu_migration", set()) & sets.get("idle_session_reclaim", set()))
    return Allocation(owners, overlap)
