from __future__ import annotations

import pandas as pd

from decision.contracts import EvaluationRequest, SampleWindow
from decision.data import DataSnapshot


def default_request() -> EvaluationRequest:
    return EvaluationRequest.model_validate_json((__import__('pathlib').Path(__file__).parents[1] / 'contracts/fixtures/default-request.json').read_text())


def golden_snapshot() -> DataSnapshot:
    jobs = pd.DataFrame([
        {"id_job":101,"id_user":1,"state_name":"COMPLETED","job_type":"batch","attempts":1,"gpu_count":1,"gpu_hours":10.0,"sm_util_avg":0.0,"sm_util_max":0.0,"walltime_sec":36000.0,"time_submit":0.0,"time_start":0.0,"time_end":36000.0},
        {"id_job":102,"id_user":1,"state_name":"COMPLETED","job_type":"LLSUB:INTERACTIVE","attempts":1,"gpu_count":2,"gpu_hours":20.0,"sm_util_avg":0.0,"sm_util_max":0.0,"walltime_sec":36000.0,"time_submit":0.0,"time_start":0.0,"time_end":36000.0},
        {"id_job":103,"id_user":2,"state_name":"CANCELLED","job_type":"LLSUB:INTERACTIVE","attempts":1,"gpu_count":2,"gpu_hours":16.0,"sm_util_avg":2.0,"sm_util_max":25.0,"walltime_sec":28800.0,"time_submit":0.0,"time_start":0.0,"time_end":28800.0},
    ])
    rows=[]
    for job,count,hours,avg,peak in [(101,1,10,0,0),(102,2,10,0,0),(103,2,8,2,25)]:
        for gpu in range(count): rows.append({"Node":f"fixture-n{job}","gpu_id":gpu,"id_job":job,"totalexecutiontime_sec":hours*3600.0,"smutilization_pct_avg":float(avg),"smutilization_pct_max":float(peak),"gpu_hours":float(hours)})
    findings=[{"id":f"finding-{job}" + ("-idle" if detector == "rules::idle-interactive-session" else ""),"detectorId":detector,"metadata":{"job_id":job},"resourceIds":[],"rootCauses":[]} for job,detector in [(101,"rules::gpu-not-needed"),(102,"rules::gpu-not-needed"),(102,"rules::idle-interactive-session"),(103,"rules::slow-cancel-of-idle-job")]]
    window=SampleWindow(start_offset_sec=0.0,end_offset_sec=36000.0,epoch_offset_sec=1750862959,mapped_start_utc="2025-06-25T12:09:19+00:00",mapped_end_utc="2025-06-25T22:09:19+00:00")
    return DataSnapshot("fixture-dataset-v1",jobs,pd.DataFrame(rows),pd.DataFrame(),pd.DataFrame(),findings,window,"test_fixture")
