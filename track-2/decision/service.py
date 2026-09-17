from __future__ import annotations
import hashlib, json, math
import numpy as np
import pandas as pd
from api.main import DEFAULT_PRICE_BOOK
from decision.baseline import compute_baseline
from decision.candidates import build_candidates
from decision.contracts import *
from decision.errors import DecisionError
from decision.portfolio import allocate_candidates
from decision.risk import compute_risk

ORDER=["cpu_migration","idle_session_reclaim"]
INFO={"cpu_migration":("Move zero-compute completed jobs to CPU","Platform engineering","Pilot CPU migration after correctness and queue-capacity checks.","medium"),"idle_session_reclaim":("Reclaim idle interactive sessions","Research platform operations","Notify at 3.5 hours, allow 0.5 hours, then reclaim with owner protections.","low")}
def _meta(s,eid=None): return Meta(dataset_id=s.dataset_id,evaluation_id=eid,data_origin=s.data_origin,sample_window=s.sample_window)
def _est(b,n,unit="gpu_hours",basis="Scenario applied to capped candidate capacity; not observed savings."): return Estimate(low=float(b.low)*n,point=float(b.point)*n,high=float(b.high)*n,unit=unit,basis=basis)
def _usd(e,p): return Estimate(low=e.low*p,point=e.point*p,high=e.high*p,unit="usd",basis="Reference GPU price scenario; not cash savings.")
def _normalized(r):
    d=r.model_dump(mode="json"); d["selected_action_ids"]=[a for a in ORDER if a in d["selected_action_ids"]]
    def walk(x):
        if isinstance(x,dict): return {k:walk(v) for k,v in x.items()}
        if isinstance(x,list): return [walk(v) for v in x]
        if isinstance(x,(int,float)) and not isinstance(x,bool): return 0.0 if float(x)==0 else float(x)
        return x
    return walk(d)
def _eid(s,r):
    raw=json.dumps({"dataset_id":s.dataset_id,"analysis_version":"track2-decision-v1","request":_normalized(r)},sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()
def _sum_risks(risks):
    values={}; specs=[("rerun_gpu_hours","gpu_hours"),("rerun_reference_cost_usd","usd"),("additional_cpu_core_hours","cpu_core_hours"),("additional_cpu_cost_usd","usd"),("added_job_hours","job_hours")]
    for name,unit in specs:
        xs=[getattr(r,name) for r in risks]; values[name]=None if any(x is None for x in xs) else Estimate(low=sum(x.low for x in xs),point=sum(x.point for x in xs),high=sum(x.high for x in xs),unit=unit,basis="Sum of selected actions' assigned-cohort scenarios.")
    return RiskResult(**values,cash_savings_usd=None,unknowns=list(dict.fromkeys(x for r in risks for x in r.unknowns)))

def evaluate(snapshot,request,investigation=None):
    request=request.model_copy(update={"selected_action_ids":[a for a in ORDER if a in request.selected_action_ids]})
    ledger=build_candidates(snapshot); allocation=allocate_candidates(ledger,request.selected_action_ids); actions=[]; risks=[]; parts=[]
    for action in ORDER:
        rows=ledger.rows[(ledger.rows.action_id==action)&ledger.rows.eligible]; b=float(rows.candidate_gpu_hours.sum()); n=len(rows)
        assigned=rows[rows.job_id.map(allocation.owner_by_job.get)==action]; ab=float(assigned.candidate_gpu_hours.sum()); an=len(assigned)
        params=getattr(request,action); standalone=_est(params.recoverable_fraction,b); marginal=_est(params.recoverable_fraction,ab) if action in request.selected_action_ids else None
        sr=compute_risk(action,b,n,request); mr=compute_risk(action,ab,an,request) if marginal else None
        if mr: risks.append(mr); parts.append(marginal)
        excluded=ledger.rows[(ledger.rows.action_id==action)&~ledger.rows.eligible]; reasons=sorted({x for xs in excluded.exclusion_reasons for x in xs}); title,owner,text,effort=INFO[action]
        pilot=Pilot(success_metrics=["Output correctness, queue capacity, completion time, and rerun load stay inside the pilot envelope."],stop_conditions=["Stop on output mismatch, valid-work interruption, or a pre-agreed duration/rerun limit breach."],rollback_steps=["Restore the original queue and resource request; disable automation while protections are reviewed."])
        actions.append(ActionEvaluation(action_id=action,title=title,owner_role=owner,action=text,effort=effort,rank=0,evidence_origin="test_fixture" if snapshot.data_origin=="test_fixture" else "real_telemetry",candidate_jobs=n,candidate_gpu_hours=b,excluded_jobs=len(excluded),exclusion_counts=[ExclusionCount(reason=x,jobs=int(sum(x in ys for ys in excluded.exclusion_reasons))) for x in reasons],finding_count=len({x for xs in ledger.rows[ledger.rows.action_id==action].finding_ids for x in xs}),standalone_recoverable_gpu_hours=standalone,standalone_reference_savings_usd=_usd(standalone,float(request.pricing.usd_per_gpu_hour)),marginal_recoverable_gpu_hours=marginal,marginal_reference_savings_usd=_usd(marginal,float(request.pricing.usd_per_gpu_hour)) if marginal else None,standalone_risk=sr,marginal_risk=mr,pilot=pilot,warnings=[]))
    effort={"low":0,"medium":1,"high":2}; ranking=sorted(actions,key=lambda a:(-a.standalone_recoverable_gpu_hours.low,-a.standalone_recoverable_gpu_hours.point,effort[a.effort],a.action_id)); rank={a.action_id:i+1 for i,a in enumerate(ranking)}; actions=[a.model_copy(update={"rank":rank[a.action_id]}) for a in actions]
    combined=Estimate(low=sum(x.low for x in parts),point=sum(x.point for x in parts),high=sum(x.high for x in parts),unit="gpu_hours",basis="Deduplicated assigned-cohort scenario; whole jobs follow CPU then idle priority.")
    baseline=compute_baseline(snapshot,request.pricing); target=.2*baseline.measured_gpu_hours; gap=Estimate(low=max(target-combined.high,0),point=max(target-combined.point,0),high=max(target-combined.low,0),unit="gpu_hours",basis="Gap to 20% of sample GPU-hours; not a budget commitment.")
    if risks: risk=_sum_risks(risks)
    else:
        z=lambda unit:Estimate(low=0,point=0,high=0,unit=unit,basis="No actions selected.")
        risk=RiskResult(rerun_gpu_hours=z("gpu_hours"),rerun_reference_cost_usd=z("usd"),additional_cpu_core_hours=z("cpu_core_hours"),additional_cpu_cost_usd=z("usd"),added_job_hours=z("job_hours"),cash_savings_usd=None,unknowns=["Cash savings are unknown without billing realization evidence."])
    portfolio=Portfolio(selected_action_ids=request.selected_action_ids,allocation_order=ORDER,unique_jobs=len(allocation.owner_by_job),overlap_jobs=allocation.overlap_jobs,recoverable_gpu_hours=combined,reference_savings_usd=_usd(combined,float(request.pricing.usd_per_gpu_hour)),risk=risk,sample_capacity_target_fraction=.2,sample_capacity_target_gpu_hours=target,sample_capacity_gap_gpu_hours=gap,caveats=["Historical capacity scenarios do not prove realized cash savings."])
    version=DEFAULT_PRICE_BOOK.version+("+custom" if float(request.pricing.usd_per_gpu_hour)!=DEFAULT_PRICE_BOOK.usd_per_gpu_hour else "")
    return Evaluation(meta=_meta(snapshot,_eid(snapshot,request)),request=request,price_book_version=version,baseline=baseline,actions=actions,portfolio=portfolio,ranking_basis="Standalone low then point recovery, effort, and action ID; allocation remains CPU then idle.",audit_status=investigation.status if investigation else "not_run",warnings=[])

def evidence_page(snapshot,request,action_id,scope,offset,limit):
    if action_id not in ORDER: raise DecisionError("NOT_FOUND","Action not found.",{"action_id":action_id},404)
    if scope not in ("standalone","marginal"): raise DecisionError("INVALID_REQUEST","Invalid evidence scope.",{"scope":scope},422)
    if scope=="marginal" and action_id not in request.selected_action_ids: raise DecisionError("ACTION_NOT_SELECTED","Marginal evidence requires a selected action.",{"action_id":action_id},422)
    ledger=build_candidates(snapshot); allocation=allocate_candidates(ledger,request.selected_action_ids); params=getattr(request,action_id); out=[]
    selected=ledger.rows[ledger.rows.action_id==action_id].sort_values("job_id",key=lambda s:s.map(int))
    for _,r in selected.iterrows():
        eligibility="included" if r.eligible else "excluded"; reasons=list(r.exclusion_reasons); amount=float(r.candidate_gpu_hours or 0)
        if scope=="marginal" and r.eligible and allocation.owner_by_job.get(r.job_id)!=action_id: eligibility="overlap_assigned_elsewhere"; reasons.append("OVERLAP_ASSIGNED_TO_CPU_MIGRATION"); amount=0
        out.append(JobEvidenceRow(job_id=r.job_id,user_id=r.user_id,state_name=r.state_name,gpu_count=r.gpu_count,measured_gpu_hours=r.measured_gpu_hours,capped_gpu_hours=r.capped_gpu_hours,candidate_gpu_hours=r.candidate_gpu_hours,contribution_gpu_hours=_est(params.recoverable_fraction,amount,basis="Row contribution to requested scope."),eligibility=eligibility,reasons=reasons,finding_ids=r.finding_ids,nodes=r.nodes))
    rows=out[offset:offset+limit]; return EvidencePage(meta=_meta(snapshot,_eid(snapshot,request)),action_id=action_id,scope=scope,rows=rows,total=len(out),offset=offset,limit=limit,next_offset=offset+limit if offset+limit<len(out) else None)

def _finite(v): return float(v) if isinstance(v,(int,float,np.integer,np.floating)) and math.isfinite(float(v)) else None
def _id(v): return str(int(v)) if isinstance(v,(int,float,np.integer,np.floating)) and float(v).is_integer() else str(v)
def job_detail(snapshot,job_id):
    found=snapshot.jobs[snapshot.jobs.id_job.map(_id)==str(job_id)]
    if found.empty: raise DecisionError("NOT_FOUND","Job not found.",{"job_id":job_id},404)
    j=found.iloc[0]; cards=snapshot.gpus[snapshot.gpus.id_job.map(_id)==str(job_id)]; g=[]
    for _,c in cards.iterrows():
        duration=_finite(c.get("totalexecutiontime_sec")); wall=_finite(j.get("walltime_sec")); flags=[]
        if duration is None or duration<0: flags.append("INVALID_GPU_DURATION")
        if duration is not None and wall is not None and duration>wall: flags.append("DURATION_CAPPED")
        g.append(GpuDetail(node=str(c.get("Node") or ""),gpu_id=int(c.get("gpu_id")),totalexecutiontime_sec=duration,smutilization_pct_avg=_finite(c.get("smutilization_pct_avg")),smutilization_pct_max=_finite(c.get("smutilization_pct_max")),measured_gpu_hours=_finite(c.get("gpu_hours")),capped_gpu_hours=min(duration,wall)/3600 if duration is not None and duration>=0 and wall is not None else None,quality_flags=flags))
    fids=[str(f.get("id")) for f in snapshot.findings if _id((f.get("metadata") or {}).get("job_id"))==str(job_id)]
    uid=_finite(j.get("id_user")); value=lambda n:_finite(j.get(n))
    nodes = j.get("nodefail_nodes")
    if nodes is None or (not isinstance(nodes, (list, tuple, np.ndarray)) and pd.isna(nodes)):
        nodes = []
    else:
        nodes = list(nodes)
    return JobDetail(meta=_meta(snapshot),job_id=str(job_id),user_id=str(int(uid)) if uid is not None else None,array_job_id=None,state_name=str(j.state_name),job_type=None if j.get("job_type") is None else str(j.job_type),attempts=int(j.get("attempts",1)),hit_node_failure=bool(j.get("hit_node_failure",False)),nodefail_nodes=nodes,nodefail_exact=bool(j.get("nodefail_exact",False)),time_submit_offset_sec=value("time_submit"),time_start_offset_sec=value("time_start"),time_end_offset_sec=value("time_end"),walltime_sec=value("walltime_sec"),measured_gpu_hours=float(j.gpu_hours),sm_util_avg=value("sm_util_avg"),sm_util_max=value("sm_util_max"),finding_ids=fids,gpus=g,quality_flags=[])
def finding_detail(snapshot,finding_id):
    f=next((x for x in snapshot.findings if str(x.get("id"))==str(finding_id)),None)
    if f is None: raise DecisionError("NOT_FOUND","Finding not found.",{"finding_id":finding_id},404)
    md=f.get("metadata") or {}; jobs=[] if md.get("job_id") is None else [_id(md["job_id"])]; roots=[str(x) for x in f.get("rootCauses",[])]; origin="test_fixture" if snapshot.data_origin=="test_fixture" else ("synthetic_incident" if md.get("synthetic") else "real_telemetry")
    return FindingDetail(meta=_meta(snapshot),finding_id=str(finding_id),detector_id=str(f.get("detectorId","")),title=str(f.get("shortDescription",f.get("title",""))),description=str(f.get("longDescription",f.get("description",""))),resource_ids=[str(x) for x in f.get("resourceIds",[])],root_cause_ids=roots,job_ids=jobs,node_names=[str(md["node"])] if md.get("node") else [],evidence_origin=origin,impact_scope=md.get("impact_scope"),impact_kind=md.get("impact_kind"),reported_impact_gpu_hours=_finite(md.get("impact_gpu_hours")),causal_status="available" if roots else "no_chain",method="Static detector evidence; no MCP investigation is implied.")
