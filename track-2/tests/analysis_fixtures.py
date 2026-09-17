from dataclasses import replace

from decision.contracts import Bounds


def clone_snapshot(snapshot, **changes):
    values = {}
    for name in ("jobs", "gpus", "resources", "edges"):
        values[name] = changes.get(name, getattr(snapshot, name).copy(deep=True))
    values["findings"] = changes.get("findings", [dict(item) for item in snapshot.findings])
    return replace(snapshot, **values)


def risk_request(default_request):
    return default_request.model_copy(update={
        "selected_action_ids": ["cpu_migration", "idle_session_reclaim"],
        "pricing": default_request.pricing.model_copy(update={"usd_per_cpu_core_hour": .1}),
        "cpu_migration": default_request.cpu_migration.model_copy(update={
            "additional_cpu_core_hours_per_gpu_hour": Bounds(low=.5, point=1, high=2),
            "rerun_gpu_hours_per_candidate_gpu_hour": Bounds(low=0, point=.1, high=.2),
            "added_elapsed_hours_per_job": Bounds(low=0, point=.5, high=1),
        }),
        "idle_session_reclaim": default_request.idle_session_reclaim.model_copy(update={
            "rerun_gpu_hours_per_candidate_gpu_hour": Bounds(low=0, point=.25, high=.5),
            "added_elapsed_hours_per_job": Bounds(low=0, point=1, high=2),
        }),
    })
