
import { Strategy as DiscordStrategy } from 'passport-discord';
import Address from './Address.js';

export function checkAuth(req, res, next) {
    if (req.isAuthenticated()) return next();
    return res.status(401).json({
        error: 'Not authenticated'
    });
}

const scopes = ['identify'];

export const authStrategy = new DiscordStrategy({
    clientID: process.env.DISCORD_CLIENT_ID,
    clientSecret: process.env.DISCORD_SECRET,
    callbackURL: process.env.DISCORD_CALLBACK_URL,
    scope: scopes
},
function(accessToken, refreshToken, profile, cb) {
    Address.findOne({
        user: profile.id,
    }, (err, address) => {
        if (err) {
            return cb(err);
        } else {
            if (process.env.TESTING) {
                console.log(`User with id ${profile.id} logged in. Address: ${address?.address}`);
            }
            const user = {
                user: profile.id,
                address: address?.address,
            }
            return cb(err, user);
        }
    });
}
)