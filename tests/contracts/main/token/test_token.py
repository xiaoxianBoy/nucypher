


import pytest
from eth_tester.exceptions import TransactionFailed

from nucypher.blockchain.eth.token import NU

TOTAL_SUPPLY = NU(1_000_000_000, 'NU').to_units()


def test_create_token(testerchain, deploy_contract):
    """
    These are tests for standard tokens taken from Consensys github:
    https://github.com/ConsenSys/Tokens/
    but some of the tests are converted from javascript to python
    """

    creator = testerchain.client.accounts[0]
    account1 = testerchain.client.accounts[1]
    account2 = testerchain.client.accounts[2]

    assert creator == testerchain.client.coinbase

    # Create an ERC20 token
    token, txhash = deploy_contract('NuCypherToken', TOTAL_SUPPLY)
    assert txhash is not None

    # Account balances
    assert TOTAL_SUPPLY == token.functions.balanceOf(creator).call()
    assert 0 == token.functions.balanceOf(account1).call()

    # Basic properties
    assert 'NuCypher' == token.functions.name().call()
    assert 18 == token.functions.decimals().call()
    assert 'NU' == token.functions.symbol().call()

    # Cannot send ETH to the contract because there is no payable function
    with pytest.raises((TransactionFailed, ValueError)):
        tx = testerchain.client.send_transaction({'from': testerchain.client.coinbase,
                                                           'to': token.address,
                                                           'value': 100,
                                                           'gasPrice': 0})
        testerchain.wait_for_receipt(tx)

    # Can transfer tokens
    tx = token.functions.transfer(account1, 10000).transact({'from': creator})
    testerchain.wait_for_receipt(tx)
    assert 10000 == token.functions.balanceOf(account1).call()
    assert TOTAL_SUPPLY - 10000 == token.functions.balanceOf(creator).call()
    tx = token.functions.transfer(account2, 10).transact({'from': account1})
    testerchain.wait_for_receipt(tx)
    assert 10000 - 10 == token.functions.balanceOf(account1).call()
    assert 10 == token.functions.balanceOf(account2).call()
    tx = token.functions.transfer(token.address, 10).transact({'from': account1})
    testerchain.wait_for_receipt(tx)
    assert 10 == token.functions.balanceOf(token.address).call()


def test_approve_and_call(testerchain, deploy_contract):
    creator = testerchain.client.accounts[0]
    account1 = testerchain.client.accounts[1]
    account2 = testerchain.client.accounts[2]

    token, _ = deploy_contract('NuCypherToken', TOTAL_SUPPLY)
    mock, _ = deploy_contract('ReceiveApprovalMethodMock')

    # Approve some value and check allowance
    tx = token.functions.approve(account1, 100).transact({'from': creator})
    testerchain.wait_for_receipt(tx)
    assert 100 == token.functions.allowance(creator, account1).call()
    assert 0 == token.functions.allowance(creator, account2).call()
    assert 0 == token.functions.allowance(account1, creator).call()
    assert 0 == token.functions.allowance(account1, account2).call()
    assert 0 == token.functions.allowance(account2, account1).call()

    # Use transferFrom with allowable value
    tx = token.functions.transferFrom(creator, account2, 50).transact({'from': account1})
    testerchain.wait_for_receipt(tx)
    assert 50 == token.functions.balanceOf(account2).call()
    assert 50 == token.functions.allowance(creator, account1).call()

    # The result of approveAndCall is increased allowance and method execution in the mock contract
    tx = token.functions.approveAndCall(mock.address, 25, testerchain.w3.toBytes(111))\
        .transact({'from': account1})
    testerchain.wait_for_receipt(tx)
    assert 50 == token.functions.balanceOf(account2).call()
    assert 50 == token.functions.allowance(creator, account1).call()
    assert 25 == token.functions.allowance(account1, mock.address).call()
    assert account1 == mock.functions.sender().call()
    assert 25 == mock.functions.value().call()
    assert token.address == mock.functions.tokenContract().call()
    assert 111 == testerchain.w3.toInt(mock.functions.extraData().call())

    # Can't approve non zero value
    with pytest.raises((TransactionFailed, ValueError)):
        tx = token.functions.approve(account1, 100).transact({'from': creator})
        testerchain.wait_for_receipt(tx)
    assert 50 == token.functions.allowance(creator, account1).call()
    # Change to zero value and set new one
    tx = token.functions.approve(account1, 0).transact({'from': creator})
    testerchain.wait_for_receipt(tx)
    assert 0 == token.functions.allowance(creator, account1).call()
    tx = token.functions.approve(account1, 100).transact({'from': creator})
    testerchain.wait_for_receipt(tx)
    assert 100 == token.functions.allowance(creator, account1).call()

    # Decrease value
    tx = token.functions.decreaseAllowance(account1, 60).transact({'from': creator})
    testerchain.wait_for_receipt(tx)
    assert 40 == token.functions.allowance(creator, account1).call()
    tx = token.functions.increaseAllowance(account1, 10).transact({'from': creator})
    testerchain.wait_for_receipt(tx)
    assert 50 == token.functions.allowance(creator, account1).call()
