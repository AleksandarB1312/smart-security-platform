from crypto.schnorr import (
    ORDER,
    create_commitment,
    create_response,
    generate_keypair,
    verify_proof,
)


def test_valid_proof_is_accepted():
    private_key, public_key = generate_keypair()
    nonce, commitment = create_commitment()
    challenge = 123456789

    response = create_response(nonce, challenge, private_key)

    assert verify_proof(commitment, challenge, response, public_key) is True


def test_proof_with_wrong_private_key_is_rejected():
    private_key, public_key = generate_keypair()
    wrong_private_key, _ = generate_keypair()
    nonce, commitment = create_commitment()
    challenge = 123456789

    fake_response = create_response(nonce, challenge, wrong_private_key)

    assert verify_proof(commitment, challenge, fake_response, public_key) is False


def test_reused_nonce_leaks_private_key():
    private_key, public_key = generate_keypair()
    nonce, commitment = create_commitment()

    challenge_one = 111
    challenge_two = 222
    response_one = create_response(nonce, challenge_one, private_key)
    response_two = create_response(nonce, challenge_two, private_key)

    recovered_key = (
        (response_one - response_two)
        * pow(challenge_one - challenge_two, -1, ORDER)
    ) % ORDER

    assert recovered_key == private_key
