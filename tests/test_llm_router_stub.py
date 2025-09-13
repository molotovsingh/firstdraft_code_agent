from shared.llm_service.router import LLMRouter


def test_llm_router_stub_complete():
    r = LLMRouter()
    out = r.complete(task_type="entity_discovery", prompt="Hello World", user_id=123)
    assert out.startswith("[LLM stub]")
    assert "entity_discovery" in out
    assert "123" in out

