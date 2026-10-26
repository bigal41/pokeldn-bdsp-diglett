# BDSP — Diglett 0.4.0

Activate the 40-point Diglett bonus, renew it automatically after expiry, or add a
custom number of points. The interface, status messages and documentation are in English.

[Download version 0.4.0](https://github.com/xCyrusBR/pokeldn-bdsp-diglett/releases/download/v0.4.0/BDSP-Diglett-Experimental-0.4.0.pokeplugin)

## Installation and use

In PokéLDN, open **Plugins → Add a plugin** and select the .pokeplugin file.
Then open **BDSP → Diglett (experimental)**.

1. On your Switch, use the Explorer Kit and enter the Grand Underground using
   **Local Communication**.
2. Stay in a tunnel, outside Hideaways, battles and digging sessions.
3. Choose an action:
   - **Activate the 40-point bonus**: send all 40 points in one message.
   - **Activate and renew automatically**: keep renewing while the tool runs.
   - **Observe session**: connect without sending points.
   - **Add custom points**: choose **Points to add (1–40)** and send that amount once.
4. Press **Start**. Check the counter and bonus on your Switch.
5. Press **Stop** to end automatic renewal.

Custom points are an amount to add, not a target counter value. For example,
adding 10 when the counter is 5 requests 15 total. Reaching 40 activates the bonus.
The game ignores new points while the bonus is active. Custom values are validated
before opening the radio; the range is 1–40. Running time controls the connection,
not the bonus duration (the interface defaults to one hour).

## Renewal behavior

Activation sends NetKousekiAdd with value 40 once. Renewal sends the same message
every five seconds. The receiver ignores it during the bonus; after expiry, the
next contribution starts a new bonus. With a stable connection, the gap is normally
up to about six seconds. This does not extend the active bonus timer.

If delivery is not acknowledged, renewal stops with an error rather than retrying
that contribution as a new collection. The plugin does not reconnect automatically.
It requires the local session and the tool to remain connected. No firmware update
is required.

The character uses the player's advertised position without an offset and may
overlap the player. Movement, Hideaways and digging during renewal remain untested;
the physical tests took place in a tunnel.

## Validation and compatibility

On 26 October 2026, the user confirmed +1, then 01/40 → 40/40, bonus activation,
and automatic reactivation after expiry on a Switch with BDSP 1.3.0.
Single +40 messages were used for the renewal test. Exact bonus duration and renewal
delay were not measured. Custom amounts other than 1, 3 and 40 have encoding and
range tests; they have not been individually checked on the console.

Tested session: scene 0x3120, app_version 199, channel 6. Tested radio: ESP32-S3,
diag-macreset-v5 firmware. Other Underground scenes remain untested.
Package parsing and tool registration were checked against PokéLDN 0.45.3's real
plugin API. The plugin requires the BDSP/LDN modules included with PokéLDN.

Local capture.jsonl and summary.json files separate delivery, ACKs and human-confirmed
game effects. An ACK alone does not prove activation. Captures may contain session
keys; keep them private. The release contains only public source files and the
license, without ROM files, keys or captures.

Development commands:

```
python service.py --action activate --seconds 90
python service.py --action renew --seconds 3600
python service.py --action custom --points 17 --seconds 90
```

Use your configured PokéLDN radio. Choose your own serial port in PokéLDN settings.
Licensed under AGPL-3.0; see LICENSE and NOTICE.md. Based on PokéLDN's BDSP transport.

## Building from source

Run `python build.py` to create the `.pokeplugin` and SHA-256 checksum under `dist/`.
Building only needs Python 3.11 or newer. Running the plugin needs PokéLDN API 1.8
or newer with the BDSP/LDN modules (checked against PokéLDN 0.45.3).
The standalone script and `test_diglett.py` should run in a PokéLDN source environment
with its dependencies installed. Run `python -m pytest test_diglett.py`.
