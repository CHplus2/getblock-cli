import httpx
import pytest
from typer.testing import CliRunner
from getblock import cli, ux


def run(text):
    return CliRunner().invoke(cli.app, ['interactive'], input=text)


def test_non_terminal_rejected_before_auth(monkeypatch):
    monkeypatch.setattr(ux, 'is_interactive', lambda: False)
    monkeypatch.setattr(cli, 'get_api_key', lambda: pytest.fail('No credentials for non-TTY input'))
    result=run('4\n')
    assert result.exit_code==2
    assert 'requires a terminal' in result.stderr


def test_exit_without_auth(monkeypatch):
    monkeypatch.setattr(ux, 'is_interactive', lambda: True)
    monkeypatch.setattr(cli, 'get_api_key', lambda: pytest.fail('Navigation does not need authentication'))
    assert run('4\n').exit_code==0


def test_account_navigation_and_client_cleanup(mock_client,monkeypatch):
    monkeypatch.setattr(ux, 'is_interactive', lambda: True)
    paths=[]
    def handler(request):
        paths.append(request.url.path)
        assert request.method=='GET'
        return httpx.Response(200,json={'balance_cents':125})
    client=mock_client(handler)
    result=run('1\n2\n4\n4\n')
    assert result.exit_code==0,result.output
    assert paths==['/api/v1/balance']
    assert 'getblock account balance' in result.stderr
    assert '125' in result.stdout
    assert client.client.is_closed


@pytest.mark.parametrize('resource,selection', [('protocols','2'),('tokens','3')])
def test_select_resource(mock_client,monkeypatch,resource,selection):
    monkeypatch.setattr(ux, 'is_interactive', lambda: True)
    paths=[]
    def handler(request):
        paths.append(request.url.path)
        assert request.method=='GET'
        if request.url.path.endswith('/one'):
            return httpx.Response(200,json={'id':'one','endpoint':'private-secret'})
        return httpx.Response(200,json={resource:[{'id':'one','name':'First'}],'total':1})
    mock_client(handler)
    result=run(selection+'\n2\n1\n2\n4\n')
    assert result.exit_code==0,result.output
    assert paths==['/api/v1/'+resource,'/api/v1/'+resource+'/one']
    assert 'private-secret' not in result.output
    assert 'getblock '+resource+' get one' in result.stderr


def test_paging_uses_returned_count(mock_client,monkeypatch):
    monkeypatch.setattr(ux, 'is_interactive', lambda: True)
    offsets=[]
    def handler(request):
        offset=int(request.url.params['offset']);offsets.append(offset)
        return httpx.Response(200,json={'protocols':[{'id':str(offset)}],'total':2})
    mock_client(handler)
    result=run('2\n1\n1\n2\n3\n4\n')
    assert result.exit_code==0,result.output
    assert offsets==[0,1]


def test_error_returns_to_menu(mock_client,monkeypatch):
    monkeypatch.setattr(ux,'is_interactive',lambda:True)
    mock_client(lambda request:httpx.Response(503,json={'error':'temporarily_unavailable'}))
    result=run('1\n1\n5\n4\n')
    assert result.exit_code==0,result.output
    assert 'temporarily_unavailable' in result.stderr


@pytest.mark.parametrize('text', ['','1\n','not-a-number\n99\n4\n'])
def test_cancel_and_invalid_choice(monkeypatch,text):
    monkeypatch.setattr(ux,'is_interactive',lambda:True)
    result=run(text)
    assert result.exit_code==(0 if '99' in text else 3),result.output


def test_human_output_with_json_profile(mock_client,monkeypatch):
    monkeypatch.setattr(ux,'is_interactive',lambda:True)
    monkeypatch.setenv('GETBLOCK_OUTPUT','json')
    mock_client(lambda request:httpx.Response(200,json={'id':'user'}))
    result=run('1\n1\n6\n')
    assert result.exit_code==0,result.output
    assert 'Id: user' in result.stdout
