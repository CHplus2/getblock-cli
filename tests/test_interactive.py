import httpx
import pytest
from typer.testing import CliRunner
from getblock import cli, ux, interactive


def run(text=''):
    return CliRunner().invoke(cli.app, ['interactive'], input=text)


def choices(monkeypatch, selections):
    monkeypatch.setattr(ux, 'is_interactive', lambda: True)
    sequence=iter(selections)
    def choose(title, options):
        selection=next(sequence)
        assert selection in options, (selection,options)
        return selection
    monkeypatch.setattr(interactive,'choose',choose)


def test_non_terminal_rejected_before_auth(monkeypatch):
    monkeypatch.setattr(ux,'is_interactive',lambda:False)
    monkeypatch.setattr(cli,'get_api_key',lambda:pytest.fail('No credentials for non-TTY input'))
    assert run().exit_code==2


def test_numbered_exit_without_auth(monkeypatch):
    monkeypatch.setattr(ux,'is_interactive',lambda:True)
    monkeypatch.setattr(cli,'get_api_key',lambda:pytest.fail('No auth for navigation'))
    assert run('9\n').exit_code==0


def test_account_navigation_and_client_cleanup(mock_client,monkeypatch):
    choices(monkeypatch,['Account','View balance','Back','Exit'])
    paths=[]
    client=mock_client(lambda request: paths.append(request.url.path) or httpx.Response(200,json={'balance_cents':125}))
    result=run()
    assert result.exit_code==0,result.output
    assert paths==['/api/v1/balance']
    assert 'getblock account balance' in result.stderr
    assert '125' in result.stdout
    assert client.client.is_closed


@pytest.mark.parametrize('name,resource,collection', [('Protocols','protocols','protocols'),('Tokens','tokens','tokens'),('Webhooks','webhooks','items'),('Address lists','address-lists','items'),('Dedicated nodes','dedicated','nodes'),('Limitless nodes','limitless','nodes')])
def test_browse_and_restore_cached_page(mock_client,monkeypatch,name,resource,collection):
    choices(monkeypatch,[name,'Open First (one)','Back','Back','Exit'])
    paths=[]
    def handler(request):
        paths.append(request.url.path)
        assert request.method=='GET'
        if request.url.path.endswith('/one'):
            return httpx.Response(200,json={'id':'one','endpoint':'private-secret'})
        return httpx.Response(200,json={collection:[{'id':'one','name':'First'}],'total':1})
    mock_client(handler)
    result=run()
    assert result.exit_code==0,result.output
    assert paths==['/api/v1/'+resource,'/api/v1/'+resource+'/one']
    assert 'private-secret' not in result.output
    assert 'getblock '+resource+' get one' in result.stderr


def test_paging_back_cache_and_filter(mock_client,monkeypatch):
    choices(monkeypatch,['Protocols','Next page','Previous page','Filter this page','Back','Exit'])
    monkeypatch.setattr(ux,'prompt',lambda *a,**kw:'zero')
    offsets=[]
    def handler(request):
        offset=int(request.url.params['offset']);offsets.append(offset)
        return httpx.Response(200,json={'protocols':[{'id':str(offset),'name':'zero' if offset==0 else 'one'}],'total':2})
    mock_client(handler)
    result=run()
    assert result.exit_code==0,result.output
    assert offsets==[0,1]


def test_error_returns_home(mock_client,monkeypatch):
    choices(monkeypatch,['Account','Show account','Exit'])
    mock_client(lambda request:httpx.Response(503,json={'error':'temporarily_unavailable'}))
    result=run()
    assert result.exit_code==0,result.output
    assert 'temporarily_unavailable' in result.stderr


def test_authentication_recovery(monkeypatch):
    choices(monkeypatch,['Account','Show account','Sign in','Exit'])
    monkeypatch.setattr(cli,'get_api_key',lambda:None)
    monkeypatch.setattr(ux,'prompt',lambda *a,**kw:'secret')
    stored=[]
    monkeypatch.setattr(cli,'save_api_key',lambda key,profile:stored.append((key,profile)))
    result=run()
    assert result.exit_code==0,result.output
    assert stored==[('secret','default')]
    assert 'secret' not in result.stdout


@pytest.mark.parametrize('text',['','1\n','not-a-number\n99\n9\n'])
def test_cancel_and_invalid_choice(monkeypatch,text):
    monkeypatch.setattr(ux,'is_interactive',lambda:True)
    result=run(text)
    assert result.exit_code==(0 if '99' in text else 3),result.output


def test_human_output_with_json_profile(mock_client,monkeypatch):
    choices(monkeypatch,['Account','Show account','Exit'])
    monkeypatch.setenv('GETBLOCK_OUTPUT','json')
    mock_client(lambda request:httpx.Response(200,json={'id':'user'}))
    result=run()
    assert result.exit_code==0,result.output
    assert 'Id: user' in result.stdout
