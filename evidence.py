"""Capture evidence, deliberately separate from physical game confirmation."""
import struct

def summarize(records):
    result = dict(ldn_associated=False, underground_join_sent=False,
                  underground_join_acked=False, increment_datagrams=0,
                  increment_acked=False, game_effect_confirmed=False,
                  received_counts=[], received_bonus_signals=0,
                  received_bonus_times=[], malformed_messages=0)
    result.update(fill_delivery_finished=False, fill_delivery_stopped=False,
                  increment_ack_count=0, renewal_ticks_acked=0, renewal_stopped=False)
    for r in records:
        kind = r.get('rec')
        if kind == 'seat': result['ldn_associated'] = True
        if kind == 'ug_join_sent': result['underground_join_sent'] = True
        if kind == 'ug_join_result': result['underground_join_acked'] = bool(r.get('reliable_acked'))
        if kind == 'diglett_probe_result':
            result['increment_acked'] = bool(r.get('reliable_acked'))
            result['increment_ack_count'] += int(bool(r.get('reliable_acked')))
        if kind == 'diglett_fill_finished': result['fill_delivery_finished'] = True
        if kind == 'diglett_fill_stopped': result['fill_delivery_stopped'] = True
        if kind == 'diglett_renew_tick': result['renewal_ticks_acked'] += 1
        if kind == 'diglett_renew_stopped': result['renewal_stopped'] = True
        if kind == 'tx_reliable_data' and r.get('label', '').startswith('Diglett +'):
            result['increment_datagrams'] += 1
        if kind != 'game_message': continue
        try:
            payload = bytes.fromhex(r.get('payload', ''))
        except (ValueError, TypeError):
            result['malformed_messages'] += 1
            continue
        if not payload or payload[0] not in (0x47, 0x48, 0x49, 0x50): continue
        if len(payload) < 3 or int.from_bytes(payload[1:3], 'big') != len(payload)-3:
            result['malformed_messages'] += 1
            continue
        if payload[0] in (0x47, 0x49, 0x50) and len(payload) != 7:
            result['malformed_messages'] += 1
            continue
        if payload[0] == 0x50:
            result['received_counts'].append(struct.unpack('<i', payload[3:])[0])
        if payload[0] == 0x49:
            result['received_bonus_times'].append(struct.unpack('<i', payload[3:])[0])
        if payload[0] == 0x48:
            result['received_bonus_signals'] += 1
    return result
