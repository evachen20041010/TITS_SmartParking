#!/usr/bin/env python3
"""M1D-0 static feasibility audit: network recirculation and ICCE information regime.

No TraCI import, no network mutation, no simulation. Python standard library only.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reachable(start: str, goal: str, graph: dict[str, list[str]]) -> bool:
    seen = {start}
    pending = [start]
    while pending:
        current = pending.pop()
        if current == goal:
            return True
        for neighbor in graph.get(current, []):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return False


def _on_directed_cycle(edge: str, graph: dict[str, list[str]]) -> bool:
    """True if edge can be revisited after >=1 actual edge transition."""
    return any(_reachable(neighbor, edge, graph) for neighbor in graph[edge])


def inspect_topology(net_file: Path, parking_file: Path) -> dict[str, Any]:
    """Inspect SUMO .net.xml connections, not simply geometric proximity."""
    network = ET.parse(net_file).getroot()
    edge_nodes = {
        element.attrib['id']: (element.get('from'), element.get('to'))
        for element in network.findall('edge')
        if element.get('function') != 'internal'
    }
    if not edge_nodes:
        raise ValueError('No non-internal edges in network')

    graph: dict[str, list[str]] = {edge: [] for edge in edge_nodes}
    for connection in network.findall('connection'):
        source, target = connection.get('from'), connection.get('to')
        if source in graph and target in graph and target not in graph[source]:
            graph[source].append(target)
    graph = {edge: sorted(neighbors) for edge, neighbors in graph.items()}

    parking_root = ET.parse(parking_file).getroot()
    areas: list[dict[str, Any]] = []
    for element in parking_root.findall('parkingArea'):
        lane = element.get('lane') or ''
        parking_edge = lane.rsplit('_', 1)[0]
        if parking_edge not in graph:
            raise ValueError(
                f"Parking area {element.get('id')}: lane {lane} references missing edge"
            )
        capacity = int(element.get('roadsideCapacity', '0'))
        if capacity < 0:
            raise ValueError(f"Parking area {element.get('id')}: negative capacity")
        areas.append({
            'id': element.attrib['id'],
            'lane': lane,
            'edge': parking_edge,
            'capacity': capacity,
            'revisitable_by_directed_cycle': _on_directed_cycle(parking_edge, graph),
        })

    if not areas:
        raise ValueError('No parking areas found')

    general_areas = [a for a in areas if a['id'].endswith('_G')]
    legal_general_capacity = sum(a['capacity'] for a in general_areas)
    if not general_areas:
        raise ValueError('General parking spaces not found')

    entrance = 'E1' if 'E1' in graph else None
    exit_edge = 'E3' if 'E3' in graph else None
    cycle_edges = sorted(edge for edge in graph if _on_directed_cycle(edge, graph))
    reachable_parking_areas = [
        a['id'] for a in areas
        if entrance is not None and _reachable(entrance, a['edge'], graph)
    ]
    revisitable_areas = [
        a['id'] for a in areas
        if a['revisitable_by_directed_cycle']
        and entrance is not None
        and _reachable(entrance, a['edge'], graph)
    ]

    return {
        'network_sha256': sha256_file(net_file),
        'parking_sha256': sha256_file(parking_file),
        'non_internal_edge_count': len(graph),
        'non_internal_edges': sorted(graph),
        'directed_connections': [
            {'from_edge': source, 'to_edge': target}
            for source in sorted(graph)
            for target in graph[source]
        ],
        'edge_from_to_nodes': {k: list(v) for k, v in edge_nodes.items()},
        'directed_cycle_edges': cycle_edges,
        'directed_cycle_exists': bool(cycle_edges),
        'reachable_parking_areas_from_E1': reachable_parking_areas,
        'revisitable_parking_areas_from_E1': revisitable_areas,
        'all_general_areas_revisitable': all(
            a['id'] in revisitable_areas for a in general_areas
        ),
        'path_E1_to_E3_exists': bool(
            entrance and exit_edge and _reachable(entrance, exit_edge, graph)
        ),
        'general_capacity_from_XML': legal_general_capacity,
        'total_capacity_from_XML': sum(a['capacity'] for a in areas),
        'parking_areas': areas,
    }


def _call_name(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    pieces: list[str] = []
    current = node.func
    while isinstance(current, ast.Attribute):
        pieces.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        pieces.append(current.id)
        return '.'.join(reversed(pieces))
    return None


def inspect_icce_behavior(script: Path) -> dict[str, Any]:
    """Conservative static evidence: never execute the frozen ICCE simulator."""
    tree = ast.parse(script.read_text(encoding='utf-8'), filename=str(script))
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    needed = ('get_zone_score', 'execute_free_search_strategy', 'run')
    if not all(name in functions for name in needed):
        raise ValueError(f'Missing expected ICCE functions: {needed}')

    score = functions['get_zone_score']
    free = functions['execute_free_search_strategy']
    run = functions['run']
    score_calls = [_call_name(node) for node in ast.walk(score) if isinstance(node, ast.Call)]
    free_calls = [_call_name(node) for node in ast.walk(free) if isinstance(node, ast.Call)]

    # The actual free-search decision occurs in the SUMO departed vehicle loop.
    departed_loop_lines: list[int] = []
    for node in ast.walk(run):
        if not isinstance(node, ast.For):
            continue
        calls = [_call_name(x) for x in ast.walk(node) if isinstance(x, ast.Call)]
        if 'execute_free_search_strategy' in calls:
            departed_loop_lines.append(node.lineno)

    top_two = False
    for node in ast.walk(free):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == 'top_candidates' for target in node.targets):
            value = node.value
            top_two = (
                isinstance(value, ast.Subscript)
                and isinstance(value.slice, ast.Slice)
                and isinstance(value.slice.upper, ast.Constant)
                and value.slice.upper.value == 2
            )

    return {
        'baseline_file_sha256': sha256_file(script),
        'zone_score_function_line': score.lineno,
        'free_search_function_line': free.lineno,
        'run_function_line': run.lineno,
        'zone_score_queries_live_parking_counts': (
            'traci.parkingarea.getVehicleCount' in score_calls
        ),
        'parking_area_stop_called_in_free_search': (
            'traci.vehicle.setParkingAreaStop' in free_calls
        ),
        'top_two_zone_candidates': top_two,
        'uses_acceptance_probability_draw': 'random.random' in free_calls,
        'free_search_invoked_inside_run_for_loop_lines': departed_loop_lines,
        'note': (
            'Evidence of live cross-zone counts and one-time decision at '
            'vehicle departure; this is NOT proof of an uninformed search '
            'or of continuous re-attempt/re-circulation.'
        ),
    }


def build_report(project_root: Path) -> dict[str, Any]:
    canonical = project_root / 'network' / 'canonical'
    net_file = canonical / 'parking_lot.net.xml'
    parking_file = canonical / 'parking_areas.add.xml'
    summary_file = project_root / 'validation' / 'network_summary.json'
    icce_file = (
        project_root.parent / '01_ICCE_2026_Frozen' / 'snapshot'
        / 'sumo_parking' / 'run_simulation.py'
    )
    for path in (net_file, parking_file, summary_file, icce_file):
        if not path.is_file():
            raise FileNotFoundError(f'Required project file absent: {path}')

    topology = inspect_topology(net_file, parking_file)
    behavior = inspect_icce_behavior(icce_file)
    summary = json.loads(summary_file.read_text(encoding='utf-8'))
    capacity_matches = (
        summary.get('status') == 'PASS'
        and summary.get('effective_capacity') == topology['general_capacity_from_XML']
        and summary.get('capacity_total') == topology['total_capacity_from_XML']
    )
    if not capacity_matches:
        raise ValueError('Canonical network capacities disagree with validated summary')

    revisit_possible = bool(topology['revisitable_parking_areas_from_E1'])
    return {
        'milestone': '1D-0',
        'analysis_kind': 'STATIC_ONLY_NO_SUMO_EXECUTION',
        'static_audit_status': 'PASS',
        'm1d_continuous_search_readiness': (
            'REVIEW_REQUIRED' if revisit_possible else 'HOLD_NO_REVISIT_LOOP'
        ),
        'network': topology,
        'original_ICCE_behavior': behavior,
        'capacity_summary_consistent': capacity_matches,
        'source_files_not_modified': True,
        'methodology_decision_required': [
            'Retain SOP canonical geometry and explicitly limit model to one pass, '
            'or approve and version a revised network with a physically explicit return path.',
            'Freeze the perceived-scarcity information rule. ICCE baseline reads '
            'current parking-area counts across zones and is information-assisted.',
            'Define failure, rejection, reroute, route-end and censoring rules '
            'without marking unparked vehicles as completed parking searches.',
        ],
        'sop_alignment': (
            'SOP v2.0 s4.1 freezes canonical geometry; s4.2 freezes information '
            'source and forbids invented guidance; Appendix A requires parameter '
            'freeze before formal Stage B.'
        ),
    }


def save_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'feasibility_audit.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    with (output_dir / 'network_adjacency.csv').open(
        'w', encoding='utf-8', newline=''
    ) as f:
        writer = csv.DictWriter(f, fieldnames=['from_edge', 'to_edge'])
        writer.writeheader()
        writer.writerows(report['network']['directed_connections'])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parent.parent
    p.add_argument('--project-root', type=Path, default=default_root)
    p.add_argument('--output-dir', type=Path, default=None)
    args = p.parse_args()
    project_root = args.project_root.resolve()
    output_dir = (
        args.output_dir.resolve() if args.output_dir is not None
        else project_root / 'validation' / 'm1d0'
    )
    report = build_report(project_root)
    save_report(report, output_dir)

    net, baseline = report['network'], report['original_ICCE_behavior']
    print('=' * 73)
    print('MILESTONE 1D-0 - STATIC FREE-SEARCH FEASIBILITY AUDIT')
    print('=' * 73)
    print(f"Canonical edges              : {', '.join(net['non_internal_edges'])}")
    print('Connections                  : ' + ', '.join(
        f"{c['from_edge']}->{c['to_edge']}" for c in net['directed_connections']
    ))
    print(f"Any directed cycle           : {net['directed_cycle_exists']}")
    print(f"Revisitable parking areas    : {net['revisitable_parking_areas_from_E1']}")
    print(f"Legal general spaces         : {net['general_capacity_from_XML']}")
    print(f"Network capacity cross-check : {'PASS' if report['capacity_summary_consistent'] else 'FAIL'}")
    print(f"ICCE live zone counts        : {baseline['zone_score_queries_live_parking_counts']}")
    print(f"ICCE top-two candidates      : {baseline['top_two_zone_candidates']}")
    print(f"ICCE acceptance draw         : {baseline['uses_acceptance_probability_draw']}")
    print(f"Static audit                 : {report['static_audit_status']}")
    print(f"1D search implementation    : {report['m1d_continuous_search_readiness']}")
    print(f'Files written                : {output_dir}')
    print('No SUMO simulation and no geometry edits were performed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
