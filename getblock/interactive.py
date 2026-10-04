"""Read-only resource browsing plus explicit credential setup."""
import copy
import os
import shlex

import typer

from getblock import ux
from getblock.http_client import GetBlockAPIError
from getblock.output import render, safe_text
from getblock.presentation import say
from getblock.workflows import choose

RESOURCES = {
    'Protocols': ('protocols', 'get_protocols', 'get_protocol', 'protocols', False),
    'Tokens': ('tokens', 'get_tokens', 'get_token', 'tokens', False),
    'Webhooks': ('webhooks', 'get_webhooks', 'get_webhook', 'items', True),
    'Address lists': ('address-lists', 'get_address_lists', 'get_address_list', 'items', True),
    'Dedicated nodes': ('dedicated', 'get_dedicated_nodes', 'get_dedicated_node', 'nodes', False),
    'Limitless nodes': ('limitless', 'get_limitless_nodes', 'get_limitless_node', 'nodes', False),
}


class Navigate(Exception):
    def __init__(self, destination):
        self.destination = destination


def menu(title, options):
    selected = choose(title, options)
    if selected in ('Home', 'Exit'):
        raise Navigate(selected)
    return selected


def show_command(*arguments):
    state = ux.current.get()
    args = ['getblock']
    if state.profile != 'default':
        args += ['--profile', state.profile]
    args += list(arguments)
    def quote(value):
        value = ux.clean(value).replace('\n', ' ').replace('\t', ' ')
        if os.name == 'nt':
            return "'" + value.replace("'", "''") + "'" if any(c.isspace() or c in "'\";$`&|()<>" for c in value) else value
        return shlex.quote(value)
    say('Command: ' + ' '.join(quote(arg) for arg in args), style='dim', err=True)
    state.operation = 'getblock ' + ' '.join(arguments[:2])


def show(data):
    render(data, output='table')


def close_clients():
    for client in ux.current.get().clients:
        client.client.close()
    ux.current.get().clients.clear()


def login():
    from getblock import cli
    close_clients()
    show_command('auth', 'login')
    if os.environ.get('GETBLOCK_API_KEY'):
        say('GETBLOCK_API_KEY overrides stored keys. Unset it in your shell to use this login.', style='yellow', err=True)
    cli.auth_login.__wrapped__(with_key=False, api="public")


def recover(error):
    ux.report(error, ux.current.get())
    close_clients()
    if getattr(error, 'code', None) == 4 or getattr(error, 'status_code', None) == 401:
        if menu('GetBlock › Authentication', ['Sign in', 'Back', 'Home', 'Exit']) == 'Sign in':
            login()


def browse(name):
    from getblock import cli
    resource, list_method, detail_method, collection, cursor_based = RESOURCES[name]
    client = cli.get_authenticated_client()
    pages, positions = [], [None if cursor_based else 0]
    page = 0
    query = ''
    while True:
        position = positions[page]
        if page == len(pages):
            params = {'limit': 20, ('cursor' if cursor_based else 'offset'): position}
            args = [resource, 'list', '--limit', '20']
            if position is not None:
                args += ['--cursor' if cursor_based else '--offset', str(position)]
            show_command(*args)
            data = getattr(client, list_method)(**params)
            if not isinstance(data, dict) or not isinstance(data.get(collection), list):
                raise ux.CLIError('The API returned an unexpected collection response.')
            pages.append(data)
        data = pages[page]
        rows = data[collection]
        visible = [row for row in rows if isinstance(row, dict) and (not query or query.casefold() in (str(row.get('id', '')) + ' ' + str(row.get('name', ''))).casefold())]
        say(f'GetBlock › {name} · Page {page + 1}', style='bold', err=True)
        show({collection: visible})
        choices = {}
        for row in visible:
            if isinstance(row.get('id'), str):
                label = 'Open ' + safe_text(row.get('name') or row['id']) + ' (' + safe_text(row['id']) + ')'
                # Duplicate rows may occur in changing collections; select by actual ID.
                choices[label] = row['id']
        next_position = data.get('next_cursor') if cursor_based else position + len(rows)
        total = data.get('total')
        more = bool(next_position) if cursor_based else bool(rows) and (not isinstance(total, int) or next_position < total)
        options = list(choices) + ['Filter this page', 'Refresh']
        if more:
            options.append('Next page')
        if page:
            options.append('Previous page')
        options += ['Back', 'Home', 'Exit']
        selected = menu('Select an item or action', options)
        if selected == 'Back':
            return
        if selected == 'Filter this page':
            query = ux.prompt('Name or ID contains (blank clears; current page only)', default='', show_default=False)
        elif selected == 'Refresh':
            pages, positions, page = [], [None if cursor_based else 0], 0
        elif selected == 'Next page':
            if cursor_based and next_position in positions[:page + 1]:
                raise ux.CLIError('The API repeated a cursor; refresh the list to continue.')
            if len(positions) == page + 1:
                positions.append(next_position)
            page += 1
        elif selected == 'Previous page':
            page -= 1
        else:
            show_command(resource, 'get', choices[selected])
            show(getattr(client, detail_method)(choices[selected]))
            menu(f'GetBlock › {name} › Details', ['Back', 'Home', 'Exit'])
            # Back restores the cached page rather than issuing another GET.


def account():
    from getblock import cli
    methods = {'Show account': ('show', 'get_me'), 'View balance': ('balance', 'get_balance'), 'View subscription': ('plan', 'get_subscription')}
    while True:
        selected = menu('GetBlock › Account', list(methods) + ['Back', 'Home', 'Exit'])
        if selected == 'Back':
            return
        command, method = methods[selected]
        show_command('account', command)
        show(getattr(cli.get_authenticated_client(), method)())


def run():
    if not ux.is_interactive():
        raise ux.CLIError('getblock interactive requires a terminal. Use direct commands in scripts; see getblock --help.', 2)
    state = copy.copy(ux.current.get() or ux.Runtime())
    state.output, state.fields = 'table', None
    state.clients, state.secrets = [], list(state.secrets)
    state.operation = 'getblock interactive'
    token = ux.current.set(state)
    try:
        say('GetBlock interactive — profile: ' + safe_text(state.profile), style='bold', err=True)
        say('Choose a number and press Enter. Advanced services use separate commands and credentials; see getblock help advanced.', style='dim', err=True)
        while True:
            try:
                selected = menu('GetBlock', ['Account', *RESOURCES, 'Login', 'Exit'])
                try:
                    if selected == 'Account':
                        account()
                    elif selected == 'Login':
                        login()
                    else:
                        browse(selected)
                except (ux.CLIError, GetBlockAPIError, ValueError, OSError) as error:
                    try:
                        recover(error)
                    except (ux.CLIError, GetBlockAPIError, ValueError, OSError) as login_error:
                        ux.report(login_error, state)
            except Navigate as navigation:
                if navigation.destination == 'Exit':
                    return
    finally:
        close_clients()
        ux.current.reset(token)
