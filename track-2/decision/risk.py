from decision.contracts import Estimate, RiskResult


def _estimate(bounds, factor, unit, basis):
    return Estimate(low=float(bounds.low) * factor, point=float(bounds.point) * factor,
                    high=float(bounds.high) * factor, unit=unit, basis=basis)


def compute_risk(action_id, candidate_gpu_hours, candidate_jobs, request):
    params = getattr(request, action_id)
    unknowns = []
    rerun = None if params.rerun_gpu_hours_per_candidate_gpu_hour is None else _estimate(params.rerun_gpu_hours_per_candidate_gpu_hour, candidate_gpu_hours, "gpu_hours", "Candidate-capacity rerun scenario; not an error probability.")
    if rerun is None: unknowns.append(f"{action_id}.rerun_gpu_hours_per_candidate_gpu_hour is unknown.")
    rerun_usd = None if rerun is None else Estimate(low=rerun.low * float(request.pricing.usd_per_gpu_hour), point=rerun.point * float(request.pricing.usd_per_gpu_hour), high=rerun.high * float(request.pricing.usd_per_gpu_hour), unit="usd", basis="Reference GPU price applied to rerun scenario.")
    added = None if params.added_elapsed_hours_per_job is None else _estimate(params.added_elapsed_hours_per_job, candidate_jobs, "job_hours", "Additional elapsed-time scenario across assigned jobs.")
    if added is None: unknowns.append(f"{action_id}.added_elapsed_hours_per_job is unknown.")
    if action_id == "idle_session_reclaim":
        cpu = Estimate(low=0, point=0, high=0, unit="cpu_core_hours", basis="Not applicable to this action.")
        cpu_usd = Estimate(low=0, point=0, high=0, unit="usd", basis="Not applicable to this action.")
    else:
        c = params.additional_cpu_core_hours_per_gpu_hour
        f = params.recoverable_fraction
        cpu = None if c is None else Estimate(low=c.low * f.low * candidate_gpu_hours, point=c.point * f.point * candidate_gpu_hours, high=c.high * f.high * candidate_gpu_hours, unit="cpu_core_hours", basis="Recovery and CPU-capacity scenario envelope.")
        if cpu is None: unknowns.append("cpu_migration.additional_cpu_core_hours_per_gpu_hour is unknown.")
        cpu_usd = None if cpu is None or request.pricing.usd_per_cpu_core_hour is None else Estimate(low=cpu.low * request.pricing.usd_per_cpu_core_hour, point=cpu.point * request.pricing.usd_per_cpu_core_hour, high=cpu.high * request.pricing.usd_per_cpu_core_hour, unit="usd", basis="Reference CPU price applied to CPU-capacity scenario.")
        if cpu is not None and cpu_usd is None: unknowns.append("pricing.usd_per_cpu_core_hour is unknown.")
    unknowns.append("Cash savings are unknown without billing realization evidence.")
    return RiskResult(rerun_gpu_hours=rerun, rerun_reference_cost_usd=rerun_usd, additional_cpu_core_hours=cpu,
                      additional_cpu_cost_usd=cpu_usd, added_job_hours=added, cash_savings_usd=None, unknowns=unknowns)
