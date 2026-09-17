"""Guards against drift between the ontology's instance data
(ontology/data-sdlc.owl and .rdfs) and apps/web/src/data/metamodel.json's
delivery_phases/delivery_artifacts, which they're meant to mirror exactly
(see docs/adr/0011-ontology-instance-data.md).

Neither ontology file is parsed by any application code at runtime — this
is a documentation-consistency check, not a functional test of app
behavior.
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
DSDLC_NS = "http://example.org/ontology/data-sdlc#"
NS = {"rdf": RDF_NS, "owl": "http://www.w3.org/2002/07/owl#", "dsdlc": DSDLC_NS}


def _local(uri):
    return uri.split("#")[-1] if uri else None


def _text(el, tag):
    child = el.find(f"dsdlc:{tag}", NS)
    return child.text if child is not None else None


def _resource_fragment(el, tag):
    child = el.find(f"dsdlc:{tag}", NS)
    if child is None:
        return None
    return _local(child.get(f"{{{RDF_NS}}}resource"))


def _load_metamodel():
    data = json.loads((root_dir / "apps/web/src/data/metamodel.json").read_text())
    phases = data["delivery_phases"]["delivery_phases"]
    artifacts = data["delivery_artifacts"]["delivery_artifacts"]
    return phases, artifacts


def _owl_individuals(class_name):
    root = ET.parse(root_dir / "ontology/data-sdlc.owl").getroot()
    out = []
    for ind in root.findall("owl:NamedIndividual", NS):
        rdf_type = ind.find("rdf:type", NS)
        if rdf_type is not None and _local(rdf_type.get(f"{{{RDF_NS}}}resource")) == class_name:
            out.append(ind)
    return out


def _rdfs_individuals(class_name):
    root = ET.parse(root_dir / "ontology/data-sdlc.rdfs").getroot()
    return root.findall(f"dsdlc:{class_name}", NS)


def _artifact_record(el, phase_id_by_uri, role_id_by_uri):
    phase_uri = _resource_fragment(el, "artifactInPhase")
    role_uri = _resource_fragment(el, "producedByRole")
    review_gate_text = el.find("dsdlc:reviewGate", NS).text
    return {
        "key": _text(el, "identifier"),
        "name": _text(el, "name"),
        "phase_key": phase_id_by_uri[phase_uri],
        "produced_by_lane": role_id_by_uri[role_uri],
        "review_gate": review_gate_text.lower() == "true",
    }


def _phase_ids_by_uri(individuals):
    return {el.get(f"{{{RDF_NS}}}about").split("#")[-1]: _text(el, "identifier") for el in individuals}


def _assert_ontology_matches_metamodel(phase_individuals, role_individuals, artifact_individuals):
    metamodel_phases, metamodel_artifacts = _load_metamodel()

    phase_ids_by_uri = _phase_ids_by_uri(phase_individuals)
    role_ids_by_uri = _phase_ids_by_uri(role_individuals)

    ontology_phase_keys = {_text(el, "identifier") for el in phase_individuals}
    assert ontology_phase_keys == {p["key"] for p in metamodel_phases}
    assert len(phase_individuals) == len(metamodel_phases)

    for el in phase_individuals:
        key = _text(el, "identifier")
        expected = next(p for p in metamodel_phases if p["key"] == key)
        assert _text(el, "name") == expected["name"]
        assert int(el.find("dsdlc:sequence", NS).text) == expected["order"]

    ontology_artifact_keys = {_text(el, "identifier") for el in artifact_individuals}
    assert ontology_artifact_keys == {a["key"] for a in metamodel_artifacts}
    assert len(artifact_individuals) == len(metamodel_artifacts) == 28

    for el in artifact_individuals:
        record = _artifact_record(el, phase_ids_by_uri, role_ids_by_uri)
        expected = next(a for a in metamodel_artifacts if a["key"] == record["key"])
        assert record["name"] == expected["name"]
        assert record["phase_key"] == expected["phase_key"]
        assert record["produced_by_lane"] == expected["produced_by_lane"]
        assert record["review_gate"] == expected["review_gate"]

    review_gated = {a["key"] for a in metamodel_artifacts if a["review_gate"]}
    assert review_gated == {"data-analyst.solution-requirements", "release-lead.deployment-checklist"}


def test_owl_instance_data_matches_metamodel():
    _assert_ontology_matches_metamodel(
        _owl_individuals("DeliveryPhase"), _owl_individuals("DeliveryRole"), _owl_individuals("DeliveryArtifact"),
    )


def test_rdfs_instance_data_matches_metamodel():
    _assert_ontology_matches_metamodel(
        _rdfs_individuals("DeliveryPhase"), _rdfs_individuals("DeliveryRole"), _rdfs_individuals("DeliveryArtifact"),
    )


def test_owl_and_rdfs_declare_the_same_artifact_identifiers():
    owl_keys = {_text(el, "identifier") for el in _owl_individuals("DeliveryArtifact")}
    rdfs_keys = {_text(el, "identifier") for el in _rdfs_individuals("DeliveryArtifact")}
    assert owl_keys == rdfs_keys


def test_four_roles_match_the_dashboard_lanes():
    from harness.project_dashboard import DEFAULT_LANE_DEFINITIONS

    lane_keys = {lane["key"] for lane in DEFAULT_LANE_DEFINITIONS}
    owl_role_keys = {_text(el, "identifier") for el in _owl_individuals("DeliveryRole")}
    rdfs_role_keys = {_text(el, "identifier") for el in _rdfs_individuals("DeliveryRole")}
    assert owl_role_keys == rdfs_role_keys == lane_keys
