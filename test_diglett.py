"""Acceptance boundaries for a non-idempotent Diglett probe."""
import importlib.util
from pathlib import Path
import sys

import pytest
import trio

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'vendor/LDN'))

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.mark.parametrize('acked', [True, False])
def test_ambiguous_ack_never_retries_or_confirms_game_effect(acked):
    transport = load('test_diglett_transport', ROOT/'bdsp_connect.py')
    sent, records = [], []
    async def send(payload, label, tries):
        sent.append((payload, tries))
        return acked
    async def run():
        return await transport.diglett_increment_once(send, lambda **r: records.append(r), 1, lambda: 0)
    assert trio.run(run) is acked
    assert sent == [(bytes.fromhex('47000401000000'), 1)]
    assert records[-1]['reliable_acked'] is acked
    assert records[-1]['game_effect_confirmed'] is False

def test_counter_and_ack_cannot_become_confirmed_bonus():
    evidence = load('test_diglett_evidence', ROOT/'evidence.py')
    result = evidence.summarize([
        dict(rec='diglett_probe_result', reliable_acked=True),
        dict(rec='game_message', payload='50000428000000'),
        dict(rec='game_message', payload='48000100'),
        dict(rec='game_message', payload='490004f0000000'),
    ])
    assert result['received_counts'] == [40]
    assert result['received_bonus_times'] == [240]
    assert result['received_bonus_signals'] == 1
    assert result['game_effect_confirmed'] is False
    assert result['underground_join_acked'] is False

@pytest.mark.parametrize('initial', [0, 1, 37, 38, 39])
def test_fill_reaches_exactly_40_without_repeating_a_delivery(initial):
    transport = load('test_fill_exact', ROOT/'bdsp_connect.py')
    values, records = [], []
    async def send(payload, label, tries):
        assert tries == 1
        values.append(int.from_bytes(payload[3:], 'little'))
        return True
    async def pause(seconds): pass
    async def run():
        return await transport.diglett_fill_once(send, lambda **r: records.append(r), initial, lambda: 0, pause)
    assert trio.run(run)
    assert initial + sum(values) == 40
    assert set(values) <= {1, 3}
    assert records[-1]['game_effect_confirmed'] is False

def test_fill_stops_on_first_ambiguous_ack():
    transport = load('test_fill_stop', ROOT/'bdsp_connect.py')
    calls, records = [], []
    async def send(payload, label, tries):
        calls.append(payload)
        return False
    async def run():
        return await transport.diglett_fill_once(send, lambda **r: records.append(r), 1, lambda: 0)
    assert trio.run(run) is False
    assert len(calls) == 1
    assert records[-1]['reason'] == 'delivery_ambiguous'

def test_malformed_frames_and_raw_compressed_data_are_not_bonus():
    evidence = load('test_diglett_malformed', ROOT/'evidence.py')
    result = evidence.summarize([dict(rec='game_message', payload=p) for p in
                                ('48040000', '50000428', '490004f000000000', 'not hex')])
    assert result['received_bonus_signals'] == 0
    assert result['received_counts'] == []
    assert result['received_bonus_times'] == []
    assert result['malformed_messages'] == 4

def test_observation_never_enables_increment_and_point_mode_requires_ug_scene():
    service = load('test_diglett_service', ROOT/'service.py')
    transport = load('test_diglett_options', ROOT/'bdsp_connect.py')
    for action, points in [('observe', 0), ('custom', 1)]:
        args = transport.build_parser().parse_args(service.arguments(action, 90, 'keys', 'capture'))
        assert args.expected_scene == 0x3120 and args.ug_join
        assert args.diglett_points == points
        assert not args.room_walk_steps
        assert not args.complete_trade and not args.inject_file
    with pytest.raises(ValueError): service.arguments('custom', 10, 'keys', 'capture')

@pytest.mark.parametrize('points', [1, 2, 17, 39, 40])
def test_custom_points_reach_transport_as_one_exact_increment(points):
    service = load('test_custom_service', ROOT/'service.py')
    transport = load('test_custom_transport', ROOT/'bdsp_connect.py')
    args = transport.build_parser().parse_args(service.arguments('custom', 90, 'keys', 'capture', points))
    assert args.diglett_points == points and not args.diglett_renew
    sent = []
    async def send(payload, label, tries):
        sent.append((payload, tries))
        return True
    async def run():
        return await transport.diglett_increment_once(send, lambda **r: None, points, lambda: 0)
    assert trio.run(run)
    assert sent == [(b'\x47\x00\x04' + points.to_bytes(4, 'little'), 1)]

@pytest.mark.parametrize('points', [0, -1, 41, 256])
def test_custom_points_reject_out_of_range_before_radio_access(points):
    service = load('test_custom_invalid', ROOT/'service.py')
    with pytest.raises(ValueError, match='between 1 and 40'):
        service.arguments('custom', 90, 'keys', 'capture', points)

def test_activation_has_bounded_budget_fresh_identity_and_no_wall_offset():
    service = load('test_activation_service', ROOT/'service.py')
    transport = load('test_activation_options', ROOT/'bdsp_connect.py')
    args = transport.build_parser().parse_args(service.arguments('activate', 90, 'keys', 'capture'))
    assert args.diglett_fill_from is None and args.diglett_points == 40
    assert args.join_offset_x == args.join_offset_z == 0
    assert args.expected_scene == 0x3120
    assert 0 < args.src_var < 0xffffffff

def test_renewal_uses_40_and_stops_after_ambiguous_delivery():
    transport = load('test_diglett_renewal', ROOT/'bdsp_connect.py')
    sent, records, sleeps = [], [], []
    async def send(payload, label, tries):
        assert payload == bytes.fromhex('47000428000000') and tries == 1
        sent.append(payload)
        return len(sent) < 3
    async def pause(seconds): sleeps.append(seconds)
    async def run():
        return await transport.diglett_renew(send, lambda **r: records.append(r), lambda: 0, pause=pause)
    assert trio.run(run) is False
    assert len(sent) == 3 and sleeps == [5, 5]
    assert records[-1]['rec'] == 'diglett_renew_stopped'
    assert not any(r.get('game_effect_confirmed') for r in records)

def test_renewal_options_keep_exact_scene_and_exclude_other_modes():
    service = load('test_renew_service', ROOT/'service.py')
    transport = load('test_renew_options', ROOT/'bdsp_connect.py')
    args = transport.build_parser().parse_args(service.arguments('renew', 3600, 'keys', 'capture'))
    assert args.diglett_renew and args.diglett_points == 0 and args.diglett_fill_from is None
    assert args.expected_scene == 0x3120 and args.hold == 3600

