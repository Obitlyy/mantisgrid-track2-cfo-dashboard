import pytest
from pydantic import ValidationError
from decision.contracts import Bounds, EvaluationRequest
from factories import default_request

def test_contract_forbids_unknown_fields_and_reversed_bounds():
    with pytest.raises(ValidationError): Bounds(low=2,point=1,high=3)
    with pytest.raises(ValidationError): EvaluationRequest.model_validate({**default_request().model_dump(),'unknown':1})
