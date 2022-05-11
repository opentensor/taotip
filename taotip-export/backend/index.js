import 'dotenv/config';
import passport from 'passport';
import { Strategy as DiscordStrategy } from 'passport-discord';
import express from 'express';
import session from 'express-session';
import MongoStore from 'connect-mongo';
import mongoose from 'mongoose';
import Address from './Address.js';
import _ from 'lodash';

import router from './routes.js';

const app = express();

const scopes = ['identify', 'email', 'guilds', 'guilds.join'];

passport.serializeUser(function(user, done) {
    done(null, user);
});
passport.deserializeUser(function(obj, done) {
    done(null, obj);
});

passport.use(new DiscordStrategy({
        clientID: process.env.DISCORD_CLIENT_ID,
        clientSecret: process.env.DISCORD_SECRET,
        callbackURL: process.env.DISCORD_CALLBACK_URL,
        scope: scopes
    },
    function(accessToken, refreshToken, profile, cb) {
        Address.findOne({
            user: profile.id,
        }, (err, address) => {
            if (err || !address) {
                cb(err);
            }
            const addr = _.omit(addr, ['_id', '__v', 'mnemonic']);
            cb(err, address);
        });
    }
));

app.use(session({
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    store: MongoStore.create({
        mongoUrl: process.env.TESTING ? process.env.MONGODB_URI_TEST : process.env.MONGODB_URI
    })
}));

app.use(passport.initialize());
app.use(passport.session());

app.use('/', express.static("build"));

app.get('/auth/discord', passport.authenticate('discord'));
app.get('/auth/discord/callback', passport.authenticate('discord', {
    failureRedirect: '/'
}), function(req, res) {
    res.redirect('/export') // Successful auth
});

app.use('/export', router);

try {
    const mongo_uri = process.env.TESTING ? process.env.MONGODB_URI_TEST : process.env.MONGODB_URI;
    await mongoose.connect(mongo_uri);
    // start express server on port 5000
    app.listen(5000, () => {
        console.log("Express server started on port 5000");
    });
} catch (error) {
    console.error('Error connecting to mongodb:', error);
}