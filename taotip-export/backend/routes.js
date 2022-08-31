"use strict";
import express from "express";
import mongoose from "mongoose";
import { checkAuth } from "./auth.js";
import { decrypt } from "./decrypt.js";
import { Keyring } from "@polkadot/keyring";
import { cryptoWaitReady } from '@polkadot/util-crypto';

const Address = mongoose.model("Address");

// /api endpoint
const router = express.Router();

router.post("/export", checkAuth, async(req, res) => {
    // Should be authenticated with Discord
    // req.user contains the address from db
    try {
        const address = await Address.findOne({
            user: String(req.user.user),
        });

        if (!address) {
            return res.status(404).json({
                error: "Address not found",
            });
        }

        if (!req.body?.password) {
            return res.status(400).json({
                error: "Password is required",
            });
        }
        // User supplied password to encrypt the mnemonic
        const password = req.body.password;

        // Must wait for crypto to be ready
        await cryptoWaitReady();
        const keyring = new Keyring({ type: "sr25519" }); // Matches bittensor cryptotype

        const encrypted_mnemonic = address.mnemonic;
        const mnemonic = await decrypt(encrypted_mnemonic);
        
        const pair = keyring.addFromMnemonic(mnemonic, { name: "taotip_export" });

        return res.json(pair.toJson(password));
    } catch (err) {
        console.log(err);
        return res.json({
            error: "Error fetching address from db",
        });
    }
});

export default router;