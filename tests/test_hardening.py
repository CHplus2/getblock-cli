import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

import httpx
import pytest
from typer.testing import CliRunner
from getblock import cli, ux
from getblock.paths import path_segment
from getblock.secret_files import secret_destination, write_secret
from getblock.output import render




@pytest.mark.parametrize('identifier',['../tokens/example','a/b','a\\b','a?query','a#fragment','.','..','%2e%2e%2ftokens','%252e%252e%252ftokens','bad\nname',''])
def test_reject_url_structure(identifier,mock_client):
    client=mock_client(lambda request:pytest.fail('Invalid ID must not reach transport'))
    with pytest.raises(ValueError):
        client.delete_webhook(identifier)


@pytest.mark.parametrize('identifier',['wh_Example-123','name with spaces','100%complete','éthereum'])
def test_valid_id_keeps_spelling(identifier,mock_client):
    def handler(request):
        from urllib.parse import unquote
        assert unquote(request.url.raw_path.decode().split('/')[-1])==identifier
        return httpx.Response(200,json={'id':identifier})
    assert mock_client(handler).get_webhook(identifier)=={'id':identifier}


@pytest.mark.parametrize('method,args', [('get_token',()),('delete_token',()),('rotate_token',()),('get_dedicated_node',()),('create_dedicated_token',('jsonrpc',)),('get_limitless_node',()),('create_limitless_token',('jsonrpc',)),('get_subscription_by_id',()),('get_protocol',()),('update_webhook',({},)),('pause_webhook',()),('resume_webhook',()),('rotate_webhook_secret',()),('send_webhook_test',()),('get_webhook_deliveries',()),('get_webhook_stats',()),('get_webhook_addresses',()),('get_address_list',()),('rename_address_list',('new',)),('delete_address_list',()),('get_address_list_entries',()),('add_address_list_entries',([],)),('replace_address_list_entries',([],)),('remove_address_list_entries',([],))])
def test_all_public_id_operations_are_guarded(mock_client,method,args):
    client=mock_client(lambda request:pytest.fail('No transport for unsafe ID'))
    with pytest.raises(ValueError):
        getattr(client,method)('../tokens/x',*args)


def test_advanced_order_id_guarded(advanced_client):
    client=advanced_client(lambda request:pytest.fail('No transport'))
    with pytest.raises(ValueError):
        client.get_tron_order('../other')


def test_private_file_and_no_overwrite(artifact_dir):
    path=artifact_dir/'secret.txt'
    with secret_destination(path) as stream:
        write_secret(stream,{'secret':'whsec_private'})
    assert path.read_text()=='whsec_private\n'
    if os.name != 'nt':
        assert path.stat().st_mode & 0o077 == 0
    with pytest.raises(OSError):
        with secret_destination(path):
            pytest.fail('Existing file must never be overwritten')
    assert path.read_text()=='whsec_private\n'


def test_save_secret_preflight_and_redaction(mock_client,artifact_dir):
    path=artifact_dir/'secret.txt'
    calls=[]
    def handler(request):
        assert path.exists()  # Reserved before HTTP.
        calls.append(request)
        return httpx.Response(200,json={'secret':'whsec_private','version':4})
    mock_client(handler)
    args=['webhooks','secret','rotate','wh_example','--yes','--save-secret',str(path)]
    result=CliRunner().invoke(cli.app,args)
    assert result.exit_code==0,result.output
    assert path.read_text()=='whsec_private\n'
    assert 'whsec_private' not in result.output
    result=CliRunner().invoke(cli.app,args)
    assert result.exit_code==1
    assert len(calls)==1


def test_secret_capture_required_before_request(mock_client):
    mock_client(lambda request:pytest.fail('Human mode requires a secret destination'))
    result=CliRunner().invoke(cli.app,['webhooks','secret','rotate','wh_example','--yes'])
    assert result.exit_code==2
    assert '--save-secret' in result.stderr


def test_secret_preview_does_not_create_file(artifact_dir):
    path=artifact_dir/'secret.txt'
    result=CliRunner().invoke(cli.app,['webhooks','secret','rotate','wh_example','--save-secret',str(path),'--dry-run','--json'])
    assert result.exit_code==0,result.output
    assert not path.exists()


def test_nested_tsv(capsys):
    render({'data':{'id':'example','status':'charged'}},'tsv','data.id,data.status')
    assert capsys.readouterr().out=='example\tcharged\n'


def test_mutation_output_failure_reports_success(mock_client):
    calls=[]
    mock_client(lambda request: calls.append(request) or httpx.Response(200,json={'secret':'whsec_private'}))
    result=CliRunner().invoke(cli.app,['webhooks','pause','wh_example','--output','tsv','--fields','missing'])
    assert result.exit_code==1
    assert len(calls)==1
    assert 'server accepted' in result.stderr
    assert 'before retrying' in result.stderr
    assert result.stdout==''


@pytest.mark.parametrize('mode,no_color,expected',[('always',False,True),('never',False,False),('always',True,False),('auto',False,False)])
def test_color_control(mock_client,monkeypatch,mode,no_color,expected):
    monkeypatch.delenv('NO_COLOR',raising=False)
    if no_color: monkeypatch.setenv('NO_COLOR','1')
    mock_client(lambda request:httpx.Response(200,json={'tokens':[{'id':'x','status':'active'}]}))
    result=CliRunner().invoke(cli.app,['--color',mode,'tokens','list'],color=True)
    assert result.exit_code==0,result.output
    assert ('\x1b[' in result.stdout)==expected


@pytest.mark.parametrize('output',['json','tsv'])
def test_color_never_enters_machine_output(mock_client,output):
    body={'tokens':[{'id':'x'}]}
    mock_client(lambda request:httpx.Response(200,json=body))
    args=['--color','always','tokens','list','--output',output]
    if output=='tsv': args += ['--fields','id']
    result=CliRunner().invoke(cli.app,args,color=True)
    assert result.exit_code==0,result.output
    assert '\x1b[' not in result.output


def test_rich_treats_api_text_as_literal(mock_client):
    mock_client(lambda request:httpx.Response(200,json={'id':'[red]literal[/red]'}))
    result=CliRunner().invoke(cli.app,['--color','always','me'],color=True)
    assert result.exit_code==0
    assert '[red]literal[/red]' in result.stdout


@pytest.mark.skipif(os.name != 'nt', reason='Windows DACL contract')
def test_windows_secret_file_has_protected_specific_acl(artifact_dir):
    import ctypes
    from ctypes import wintypes
    path=artifact_dir/'acl-secret.txt'
    with secret_destination(path) as stream:
        write_secret(stream,{'secret':'private'})
    api=ctypes.WinDLL('advapi32',use_last_error=True)
    api.GetFileSecurityW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    size=wintypes.DWORD()
    api.GetFileSecurityW(str(path),4,None,0,ctypes.byref(size))
    buffer=ctypes.create_string_buffer(size.value)
    assert api.GetFileSecurityW(str(path),4,buffer,size,ctypes.byref(size))
    convert=api.ConvertSecurityDescriptorToStringSecurityDescriptorW
    convert.argtypes=[ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(wintypes.DWORD)]
    text=ctypes.c_void_p()
    assert convert(buffer,1,4,ctypes.byref(text),None)
    try:
        sddl=ctypes.wstring_at(text)
        assert sddl.startswith('D:P')
        for broad in (';;;WD)', ';;;AU)', ';;;BU)', ';;;BA)', ';;;RC)'):
            assert broad not in sddl
    finally:
        kernel=ctypes.WinDLL('kernel32')
        kernel.LocalFree.argtypes=[ctypes.c_void_p]
        kernel.LocalFree(text)


def test_long_ids_are_preserved_on_narrow_terminals(mock_client,monkeypatch):
    monkeypatch.delenv('NO_COLOR',raising=False)
    monkeypatch.setenv('COLUMNS','30')
    identifier='long-identifier-'*8
    mock_client(lambda request:httpx.Response(200,json={'tokens':[{'id':identifier,'status':'active'}]}))
    result=CliRunner().invoke(cli.app,['--color','always','tokens','list'],color=True)
    assert result.exit_code==0,result.output
    assert identifier in result.stdout
    assert 'Result 1' in result.stdout
