"""Bounded development probe using the existing BDSP transport."""
import argparse
import importlib.util
import json
import os
import secrets
from pathlib import Path
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent

def status(message, tone='info'):
    try:
        from pokeldn import panel
    except ImportError:
        print('[diglett]', message)
    else:
        panel.show('diglett-status', 'Diglett bonus', [message], tone=tone)

def event_status(event, action):
    kind = event.get('rec')
    if kind == 'seat': status('Connected to the Switch. Joining the Grand Underground.')
    elif kind == 'ug_join_result' and not event.get('reliable_acked'):
        status('Entry not acknowledged. No points sent.', 'warning')
    elif kind == 'diglett_probe_result' and action != 'renew':
        status('Points sent. Check the counter and bonus on your Switch.' if event.get('reliable_acked')
               else 'Delivery not acknowledged. Check your Switch before trying again.',
               'info' if event.get('reliable_acked') else 'warning')
    elif kind == 'diglett_renew_tick':
        status('Renewal running. After the bonus ends, another attempt follows within about 6 seconds.')
    elif kind == 'diglett_renew_stopped':
        status('Renewal stopped: delivery not acknowledged. Check the connection and your Switch.', 'warning')

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def arguments(action, seconds, keys, capture, points=1):
    if action not in ('activate', 'renew', 'observe', 'custom'): raise ValueError('Invalid action')
    if not 30 <= seconds <= 86400: raise ValueError('Running time must be 30 to 86400 seconds')
    if not 1 <= points <= 40: raise ValueError('Points must be between 1 and 40')
    result = ['--keys', str(keys), '--expected-scene', '0x3110,0x3120,0x3140',
            '--src-var', hex(secrets.randbelow(0xfffffffe) + 1),
            '--name', 'Diglett', '--hold', str(seconds), '--channels', '1,6,11',
            '--count', '9', '--connect', '3', '--join', '4', '--reliable-ack', '--answer-requests',
            '--ug-join', '--room-walk-steps', '0', '--join-offset-x', '0',
            '--join-offset-z', '0', '--capture', str(capture),
            '--diglett-points', str({'activate': 40, 'custom': points}.get(action, 0))]
    if action == 'renew': result += ['--diglett-renew']
    return result

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action', choices=('activate', 'renew', 'observe', 'custom'), default='activate')
    parser.add_argument('--points', type=int, choices=range(1, 41), default=1,
                        help='Points to add once in custom mode (1–40)')
    parser.add_argument('--seconds', type=int, default=90)
    parser.add_argument('--keys', default=None)
    parser.add_argument('--output-dir')
    parser.add_argument('--check-only', action='store_true')
    return parser

def main(argv=None):
    args = build_parser().parse_args(argv)
    # Validate before touching the radio or creating output files.
    arguments(args.action, args.seconds, '', '', args.points)
    transport = HERE/'bdsp_connect.py'
    repo = HERE.parents[1]
    if not transport.exists(): transport = repo/'bin/bdsp_connect.py'
    if not transport.is_file(): raise ValueError('BDSP transport is missing')
    if args.check_only:
        print(json.dumps(dict(action=args.action, seconds=args.seconds,
                              max_increment_datagrams=None if args.action == 'renew' else int(args.action != 'observe'),
                              requested_points=args.points if args.action == 'custom' else None,
                              expected_scene='0x3110,0x3120,0x3140', console_tested=False)))
        return 0
    keys = args.keys
    if not keys:
        candidates = [Path.home()/'.switch/prod.keys',
            Path(os.environ.get('LOCALAPPDATA', str(Path.home())))/'PokeLDN-WonderCard-Manager/prod.keys']
        keys = next((p for p in candidates if p.is_file()), candidates[0])
    if not Path(keys).expanduser().is_file(): raise ValueError('prod.keys not found')
    if args.output_dir:
        output = Path(args.output_dir)
    else:
        try:
            from pokeldn.plugins import data_folder
            output = Path(data_folder('bdsp-diglett'))
        except ImportError:
            output = repo/'runs/bdsp-diglett'
        output /= datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True, exist_ok=True)
    capture = output/'capture.jsonl'
    if capture.exists(): raise ValueError('This folder already contains a capture; use a new folder')
    module = load('bdsp_diglett_transport', transport)
    config = module.build_parser().parse_args(arguments(args.action, args.seconds, keys, capture, args.points))
    config.event_sink = lambda event: event_status(event, args.action)
    status('Waiting for a local Grand Underground session.')
    print({'activate': 'Grand Underground: send all 40 points at once.',
           'renew': 'Grand Underground: activate and renew after expiry; five-second interval.',
           'custom': f'Grand Underground: add {args.points} points once.',
           'observe': 'Grand Underground: observing without sending points.'}[args.action])
    print('Report:', output)
    code = 1
    try:
        code = module.trio.run(module.main_async, config)
        if code == 3: status('Session not found. Enter using Local Communication on your Switch.', 'warning')
        return code
    finally:
        records = []
        if capture.exists():
            for line in capture.read_text(encoding='utf-8').splitlines():
                try: records.append(json.loads(line))
                except json.JSONDecodeError: pass
        summary = load('diglett_evidence', HERE/'evidence.py').summarize(records)
        summary.update(action=args.action, transport_exit=code,
                       requested_points=args.points if args.action == 'custom' else None)
        (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
        print('Evidence:', json.dumps(summary, ensure_ascii=False))

if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
