import express from 'express';
import mongoose from 'mongoose';
import { checkAuth } from './auth.js';
import { decrypt } from './decrypt.js';
import { Keyring } from '@polkadot/keyring';

const Address = mongoose.model('Address');

// /api endpoint
const router = express.Router();

router.post('/export', checkAuth, async(req, res) => {
    // Should be authenticated with Discord
    // req.user contains the address from db
    try {
        const address = await Address.findOne({
            'address': req.user.address
        })

        if (!address) {
            return res.status(404).json({
                error: 'Address not found'
            });
        }

        if (!req.body.password) {
            return res.status(400).json({
                error: 'Password is required'
            });
        }
        // User supplied password to encrypt the mnemonic
        const password = req.body.password;

        const keyring = new Keyring({ type: 'sr25519' }); // Matches bittensor cryptotype

        const encrypted_mnemonic = address.mnemonic;
        const mnemonic = await decrypt(encrypted_mnemonic);

        const pair = keyring.addFromMnemonic(mnemonic, { name: 'toexport' });
        const address_to_export = pair.address;
        if (address_to_export !== req.user.address) {
            return res.status(500).json({
                error: 'Server error'
            });
        }

        return res.json({
            exportedJson: pair.toJson(password)
        });
    } catch (err) {
        console.log(err);
        return res.json({
            error: "Error fetching address from db"
        })
    }
});

export default router;