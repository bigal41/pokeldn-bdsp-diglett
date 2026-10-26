"""Registration is offline; the radio is opened only when the tool runs."""
def register(api):
    from pokeldn.plugins import Field, Tool
    api.add_tool('bdsp', Tool('bdsp-diglett', 'Diglett (experimental)', 'service.py',
        'Complete the 40 Diglett points and activate the bonus in a local session.',
        ('On your Switch, enter the Grand Underground using Local Communication.',
         'Stay in a tunnel, outside Hideaways and digging sessions.',
         'Choose one activation, automatic renewal, or a custom number of points. Press Stop to end.'),
        fields=(
            Field('--action', 'Action', 'choice', default='activate',
                  choices=(('activate', 'Activate the 40-point bonus'),
                           ('renew', 'Activate and renew automatically'),
                           ('observe', 'Observe session'), ('custom', 'Add custom points'))),
            Field('--points', 'Points to add (1–40)', 'number', default='1',
                  when=('--action', 'custom'),
                  help='Adds this many points once. New points are ignored while the bonus is active.'),
            Field('--seconds', 'Running time in seconds', 'number', default='3600'),
        ), doc='README.md'))
