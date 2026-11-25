"""Create readable test case content without modifying Azure DevOps source fields."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser


class _TextParser(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts = []
        self._blocks = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4"}

    def handle_starttag(self, tag, attrs):
        if tag in self._blocks:
            self._parts.append("\n")
        elif tag in {"td", "th"}:
            self._parts.append("\t")

    def handle_endtag(self, tag):
        if tag in self._blocks:
            self._parts.append("\n")

    def handle_data(self, data):
        self._parts.append(data)


def html_to_text(value: str) -> str:
    parser = _TextParser()
    parser.feed(value)
    parser.close()
    lines = [
        re.sub(r"[^\S\n]+", " ", line).strip()
        for line in "".join(parser._parts).splitlines()
    ]
    return "\n".join(line for line in lines if line)


_TEXT_FIELDS = {
    "System.Description": "description",
    "System.History": "history",
    "Microsoft.VSTS.TCM.ReproSteps": "repro_steps",
    "Microsoft.VSTS.CMMI.Purpose": "purpose",
    "Custom.Preconditions": "preconditions",
    "Custom.EnvironmentDetails": "environment_details",
}


def normalize_test_case(work_item: dict) -> dict:
    fields = work_item.get("fields", {})
    result = {"title": fields.get("System.Title", ""), "steps": []}

    for source, target in _TEXT_FIELDS.items():
        value = fields.get(source)
        if isinstance(value, str):
            result[target] = html_to_text(value)

    steps = fields.get("Microsoft.VSTS.TCM.Steps")
    if not steps:
        return result

    try:
        root = ET.fromstring(steps)
    except ET.ParseError:
        result["steps_error"] = (
            "Não foi possível interpretar o XML dos passos; consulte o campo original."
        )
        return result

    for element in root:
        if element.tag == "step":
            values = [
                html_to_text("".join(part.itertext()))
                for part in element.findall("parameterizedString")
            ]
            result["steps"].append(
                {
                    "id": element.get("id"),
                    "type": element.get("type"),
                    "action": values[0] if values else "",
                    "expected_result": values[1] if len(values) > 1 else "",
                    **({"additional_values": values[2:]} if len(values) > 2 else {}),
                }
            )
        elif element.tag == "compref":
            result["steps"].append(
                {
                    "type": "shared_steps",
                    "id": element.get("id"),
                    "ref": element.get("ref"),
                }
            )
        else:
            result["steps"].append(
                {"type": "unknown", "xml": ET.tostring(element, encoding="unicode")}
            )
    return result
