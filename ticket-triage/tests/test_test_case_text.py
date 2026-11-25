from app.services.test_case_text import html_to_text, normalize_test_case


def test_html_preserves_blocks_and_decodes_entities():
    assert (
        html_to_text(
            "<div>Primeiro&nbsp;item<br>Segundo &amp; terceiro</div><p>Fim</p>"
        )
        == "Primeiro item\nSegundo & terceiro\nFim"
    )


def test_steps_keep_action_result_and_shared_reference():
    item = {
        "fields": {
            "System.Title": "Caso",
            "Custom.Preconditions": "<p>Pré-condição</p>",
            "Microsoft.VSTS.TCM.Steps": '<steps><step id="1" type="ValidateStep"><parameterizedString>&lt;p&gt;Ação&lt;/p&gt;</parameterizedString><parameterizedString>&lt;div&gt;Resultado&lt;/div&gt;</parameterizedString></step><compref id="2" ref="123"/></steps>',
        }
    }
    result = normalize_test_case(item)
    assert result["preconditions"] == "Pré-condição"
    assert result["steps"] == [
        {
            "id": "1",
            "type": "ValidateStep",
            "action": "Ação",
            "expected_result": "Resultado",
        },
        {"type": "shared_steps", "id": "2", "ref": "123"},
    ]
    assert item["fields"]["Custom.Preconditions"] == "<p>Pré-condição</p>"


def test_invalid_steps_remain_available_in_original():
    item = {"fields": {"Microsoft.VSTS.TCM.Steps": "<steps>"}}
    assert "steps_error" in normalize_test_case(item)
    assert item["fields"]["Microsoft.VSTS.TCM.Steps"] == "<steps>"
