import importlib.util
import json
import sys
import types
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[2]
# No production .env, database credentials or network access are needed.
database = types.ModuleType('database')
database.engine = MagicMock()
prior = sys.modules.get('database')
sys.modules['database'] = database
spec = importlib.util.spec_from_file_location('tested_backend', ROOT / 'backend/main.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
if prior is None:
    del sys.modules['database']
else:
    sys.modules['database'] = prior
SCHEMA = json.loads((ROOT / 'contracts/read-endpoints.schema.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(SCHEMA)


def validate(name, body):
    Draft202012Validator(dict(SCHEMA, **{'$ref': '#/$defs/' + name, 'oneOf': [ {'$ref': '#/$defs/' + name} ]}), format_checker=FormatChecker()).validate(body)


@pytest.fixture
def client(monkeypatch):
    engine = MagicMock()
    monkeypatch.setattr(api, 'engine', engine)
    connection = engine.connect.return_value.__enter__.return_value
    api.app.dependency_overrides[api.current_user_id] = lambda: 7
    with TestClient(api.app) as c:
        yield c, connection
    api.app.dependency_overrides.clear()


def result(first=None, rows=None, scalar=0):
    r = MagicMock()
    r.first.return_value = first
    r.mappings.return_value.first.return_value = first
    r.mappings.return_value.all.return_value = rows or []
    r.scalar_one.return_value = scalar
    return r


def wallet():
    return dict(wallet_id=1,currency='TRY',cash_balance=Decimal('900.00'),realized_pnl=Decimal('0.00'),updated_at=datetime.now(timezone.utc))


def test_history_order_and_contract(client):
    c, db = client
    now = datetime.now(timezone.utc)
    def quote(t, price):
        return dict(symbol='DEMO',price=Decimal(price),currency='TRY',as_of=t,provider='LIVE',is_delayed=False)
    db.execute.side_effect = [result(first=('DEMO',)),result(rows=[quote(now,'12.00'),quote(now-timedelta(seconds=5),'10.00')])]
    response=c.get('/api/v1/stocks/DEMO/history?limit=2')
    assert response.status_code==200
    body=response.json(); validate('PriceHistory',body)
    assert body['count']==2 and [x['price'] for x in body['history']]==['10.00','12.00']
    assert db.execute.call_args.args[1]['limit']==2


@pytest.mark.parametrize('path', ['/api/v1/stocks/DEMO/history?limit=501','/api/v1/stocks/bad.code/history','/api/v1/wallets/wallet:1/trades?offset=-1'])
def test_invalid_query(client,path):
    c,db=client
    assert c.get(path).status_code==422
    db.execute.assert_not_called()


def test_missing_stock(client):
    c,db=client; db.execute.return_value=result()
    assert c.get('/api/v1/stocks/DEMO/history').status_code==404


def test_empty_history(client):
    c,db=client; db.execute.side_effect=[result(first=('DEMO',)),result()]
    body=c.get('/api/v1/stocks/DEMO/history').json(); validate('PriceHistory',body)
    assert body['history']==[] and body['count']==0


def test_trade_history_contract_and_pagination(client):
    c,db=client; now=datetime.now(timezone.utc)
    row=dict(trade_id=1,wallet_id=1,symbol='DEMO',side='SELL',currency='TRY',quantity=2,price=Decimal('12'),total_amount=Decimal('24'),realized_pnl=Decimal('4'),quote_as_of=now,executed_at=now,idempotency_key='03eedb78-d21d-47d0-b60f-0d001796f653')
    db.execute.side_effect=[result(first=wallet()),result(scalar=2),result(rows=[row])]
    body=c.get('/api/v1/wallets/wallet:1/trades?limit=1').json(); validate('TradeHistory',body)
    assert body['has_more'] and body['items'][0]['realized_pnl']=='4.00'
    assert db.execute.call_args_list[0].args[1]['user_id']==7


@pytest.mark.parametrize('suffix',['trades','valuation'])
def test_wallet_access(client,suffix):
    c,db=client; db.execute.return_value=result()
    assert c.get('/api/v1/wallets/wallet:1/'+suffix).status_code==404
    assert db.execute.call_count==1
    db.reset_mock()
    assert c.get('/api/v1/wallets/invalid/'+suffix).status_code==400
    db.execute.assert_not_called()


@pytest.mark.parametrize('suffix',['trades','valuation'])
def test_auth_required(client,suffix):
    c,db=client; api.app.dependency_overrides.clear()
    assert c.get('/api/v1/wallets/wallet:1/'+suffix).status_code==401
    db.execute.assert_not_called()


@pytest.mark.parametrize('state',['current','stale','test','missing','currency_mismatch','invalid'])
def test_valuation_states(client,state):
    c,db=client; now=datetime.now(timezone.utc)
    row=dict(symbol='DEMO',quantity=2,average_cost=Decimal('10'),last_price=Decimal('12'),quote_currency='TRY',quote_as_of=now,provider='LIVE',is_delayed=False)
    if state=='stale': row['quote_as_of']=now-timedelta(days=1)
    if state=='test': row['provider']='TEST'
    if state=='missing': row['last_price']=None
    if state=='currency_mismatch': row['quote_currency']='USD'
    if state=='invalid': row['last_price']=Decimal('-1')
    db.execute.side_effect=[result(first=wallet()),result(rows=[row])]
    response=c.get('/api/v1/wallets/wallet:1/valuation'); assert response.status_code==200
    body=response.json(); validate('PortfolioValuation',body)
    assert body['positions'][0]['price_status']==state
    complete=state in ['current','stale','test']
    assert body['valuation_complete']==complete
    assert body['valuation_is_current']==(state=='current')
    assert body['portfolio_value']==('924.00' if complete else None)
    assert body['unrealized_pnl']==('4.00' if complete else None)


def test_cash_only_wallet(client):
    c,db=client; db.execute.side_effect=[result(first=wallet()),result()]
    body=c.get('/api/v1/wallets/wallet:1/valuation').json(); validate('PortfolioValuation',body)
    assert body['portfolio_value']=='900.00' and body['valuation_complete']
    assert not body['valuation_is_current']


@pytest.mark.parametrize('path',['/api/v1/stocks/DEMO/history','/api/v1/wallets/wallet:1/trades','/api/v1/wallets/wallet:1/valuation'])
def test_database_failure(client,path):
    c,db=client; db.execute.side_effect=SQLAlchemyError('private error')
    response=c.get(path)
    assert response.status_code==503 and 'private error' not in response.text
