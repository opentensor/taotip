import fernet from 'fernet';

export function decrypt(encrypted_mnemonic) {
    const key = new fernet.Secret(process.env.FERNET_KEY);
    var token = new fernet.Token({
        secret: key,
        token: encrypted_mnemonic,
        ttl: 0
    })
    const mnemonic = token.decode();
    return mnemonic;
}