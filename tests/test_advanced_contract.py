import copy
import json

import httpx
import pytest
from typer.testing import CliRunner

from advanced_payloads import AML_ADDRESS, AML_TRANSACTION, ORDER, WALLET, RUG_PULL
from getblock import cli, ux
from getblock.client import GetBlockAPIError


def run(args, **kwargs):
    return CliRunner().invoke(cli.app, args, **kwargs)


@pytest.mark.parametrize('asset', [None, 'usdt', ''])
def test_asset_client(advanced_client, asset):
    def handler(request):
        assert request.url.path == '/v1/aml/tx-check'
        assert json.loads(request.content) == {'tx': 'test', 'network': 'eth', **({} if asset is None else {'asset': asset})}
        return httpx.Response(200, json=AML_TRANSACTION)
    assert advanced_client(handler).check_aml_transaction('test', 'eth', asset) == AML_TRANSACTION


@pytest.mark.parametrize('source', ['flags', 'stdin', 'file'])
@pytest.mark.parametrize('asset', [None, 'usdt', ''])
def test_asset_cli_input(advanced_client, monkeypatch, source, asset):
    body = {'tx': 'test', 'network': 'eth', **({} if asset is None else {'asset': asset})}
    def handler(request):
        assert json.loads(request.content) == body
        return httpx.Response(200, json=AML_TRANSACTION)
    advanced_client(handler)
    if source == 'flags':
        args = ['--tx', 'test', '--network', 'eth'] + ([] if asset is None else ['--asset', asset])
    else:
        args = ['--input', '-' if source == 'stdin' else 'request.json']
        if source == 'file':
            from pathlib import Path
            original = Path.read_text
            monkeypatch.setattr(Path, 'read_text', lambda path, **kwargs: json.dumps(body) if path.name == 'request.json' else original(path, **kwargs))
    result = run(['aml', 'tx-check', *args, '--yes', '--json'], input=json.dumps(body))
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == AML_TRANSACTION


@pytest.mark.parametrize('asset', [None, 1, False, [], {}])
def test_asset_input_requires_string(asset):
    result = run(['aml', 'tx-check', '--input', '-', '--dry-run', '--json'], input=json.dumps({'tx':'test','network':'eth','asset':asset}))
    assert result.exit_code == 2
    assert 'must be a string' in result.stderr


def test_asset_conflicts_with_input():
    result = run(['aml', 'tx-check', '--asset', 'usdt', '--input', '-', '--dry-run', '--json'], input='{"tx":"test","network":"eth"}')
    assert result.exit_code == 2
    assert 'conflicts' in result.stderr


@pytest.mark.parametrize('amounts', [(0,125), (9223372036854775806,9223372036854775807)])
def test_402_exception_and_cli(advanced_client, amounts):
    have, need = amounts
    payload = {'error':'insufficient_balance','have_cents':have,'need_cents':need}
    client = advanced_client(lambda request: httpx.Response(402, json=payload))
    with pytest.raises(GetBlockAPIError) as caught:
        client.check_aml_transaction('test','eth')
    error = caught.value
    assert (error.have_cents,error.need_cents) == amounts
    assert error.api_error_code == 'insufficient_balance'
    assert str(error) == f'insufficient_balance (have_cents={have}, need_cents={need})'
    result = run(['aml','tx-check','--tx','test','--network','eth','--yes','--json'])
    assert result.exit_code == 1
    assert result.stdout == ''
    detail=json.loads(result.stderr)['error']
    assert (detail['have_cents'],detail['need_cents']) == amounts
    assert type(detail['have_cents']) is int
    assert detail['api_error_code'] == 'insufficient_balance'
    assert detail['message'] == str(error)


@pytest.mark.parametrize('value', [None, True, 1.5, '125', {}])
def test_402_does_not_coerce_invalid_amounts(advanced_client, value):
    client=advanced_client(lambda request:httpx.Response(402,json={'error':'insufficient_balance','have_cents':value,'need_cents':125}))
    with pytest.raises(GetBlockAPIError) as caught:
        client.check_aml_transaction('test','eth')
    assert caught.value.have_cents is None
    assert caught.value.need_cents == 125


@pytest.mark.parametrize('output', ['json','table'])
def test_upstream_diagnostic_redaction(advanced_client, output):
    secret='private-quote'
    payload={'error':'upstream_error','message':'Provider rejected '+secret}
    client=advanced_client(lambda request:httpx.Response(502,json=payload))
    with pytest.raises(GetBlockAPIError) as caught:
        client.check_wallet('ETH','test')
    assert caught.value.upstream_message == payload['message']
    assert caught.value.api_error_code == 'upstream_error'
    assert str(caught.value) == 'upstream_error'
    result=run(['tron-energy','delegate-energy','--target-address','T'+'A'*33,'--volume','1','--duration','test','--quote-token',secret,'--yes','--output',output])
    assert result.exit_code == 1
    assert secret not in result.output
    assert 'Provider rejected [redacted]' in result.stderr
    if output=='json':
        detail=json.loads(result.stderr)['error']
        assert detail['api_error_code']=='upstream_error'
        assert detail['message']=='upstream_error'
        assert detail['upstream_message']=='Provider rejected [redacted]'


@pytest.mark.parametrize('status,code', [(400,1),(401,4),(404,1),(409,1),(429,1),(502,1),(503,1)])
def test_public_error_compatibility(mock_client,status,code):
    mock_client(lambda request:httpx.Response(status,json={'error':'public_error','message':'unrelated diagnostic','request_id':'req-test'}))
    result=run(['me','--json'])
    assert result.exit_code==code
    detail=json.loads(result.stderr)['error']
    assert detail['message']=='public_error'
    assert detail['api_error_code']=='public_error'
    assert detail['request_id']=='req-test'
    assert detail['status_code']==status
    assert 'upstream_message' not in detail
    assert 'have_cents' not in detail
    assert 'need_cents' not in detail


def test_public_402_additive_fields(mock_client):
    mock_client(lambda request:httpx.Response(402,json={'error':'insufficient_balance','have_cents':0,'need_cents':10}))
    result=run(['me','--json'])
    assert result.exit_code==1
    detail=json.loads(result.stderr)['error']
    assert detail['message']=='insufficient_balance (have_cents=0, need_cents=10)'
    assert detail['have_cents']==0 and detail['need_cents']==10


@pytest.mark.parametrize('command,body', [(['wallet-audit','audit'],WALLET), (['wallet-audit','check'],WALLET), (['rug-pull','check'],RUG_PULL)])
@pytest.mark.parametrize('score', ['0.0421858616',0.0421858616])
def test_probability_and_allowed_extra_fields(advanced_client,command,body,score):
    response=copy.deepcopy(body)
    response['data']['probabilityFraud']=score
    response['data']['provider_extra']={'values':[1,False,None]}
    advanced_client(lambda request:httpx.Response(200,json=response))
    arg='--contract-address' if command[0]=='rug-pull' else '--address'
    for output in ('json','table'):
        result=run([*command,'--network','ETH',arg,'test','--yes','--output',output])
        assert result.exit_code==0,result.output
        if output=='json':
            assert json.loads(result.stdout)==response
            assert type(json.loads(result.stdout)['data']['probabilityFraud']) is type(score)
        else:
            assert str(score) in result.stdout


def test_complete_aml_examples(advanced_client):
    for command,response,flag in [('wallet-check',AML_ADDRESS,'--address'),('tx-check',AML_TRANSACTION,'--tx')]:
        advanced_client(lambda request:httpx.Response(200,json=response))
        result=run(['aml',command,flag,'test','--network','eth','--yes','--json'])
        assert result.exit_code==0,result.output
        assert json.loads(result.stdout)==response
    assert set(AML_TRANSACTION['data']['counterparties'])=={'in','out'}
    assert AML_ADDRESS['data']['attribution']['assetRestrictions']==[{'asset':'usdt'}]


def test_resource_order_list_and_pagination(advanced_client):
    requests=[]
    def handler(request):
        requests.append(request)
        offset=int(request.url.params['offset'])
        body=copy.deepcopy(ORDER['data'])
        if offset: body['id']='44a33415-21f6-45a9-b529-91e6503f6c1b'.replace('44a','55a',1)
        return httpx.Response(200,json={'data':[body],'total':2})
    advanced_client(handler)
    result=run(['tron-energy','orders','list','--limit','1','--paginate','--json'])
    assert result.exit_code==0,result.output
    pages=json.loads(result.stdout)
    assert len(pages)==2 and all(page['total']==2 for page in pages)
    assert pages[0]['data']==[ORDER['data']]
    assert [r.url.params['offset'] for r in requests]==['0','1']


def test_raw_json_passthrough_separate_from_aml_models(advanced_client):
    response={'data':{'arbitrary':[None,False,{'nested':1}]}}
    client=advanced_client(lambda request:httpx.Response(200,json=response))
    # Exercise shared decoding without claiming this is an AMLAddressReport.
    assert client._request('GET','/v1/tron-energy/orders').json()==response
