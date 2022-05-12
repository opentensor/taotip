import 'dotenv/config';
import passport from 'passport';
import { Strategy as DiscordStrategy } from 'passport-discord';
import express from 'express';
import session from 'express-session';
import MongoStore from 'connect-mongo';
import mongoose from 'mongoose';
import Address from './Address.js';
import _ from 'lodash';
import cors from 'cors';

import router from './routes.js';

const app = express();

const scopes = ['identify'];

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
            const addr = _.omit(address, ['_id', '__v', 'mnemonic']);
            if (process.env.TESTING) {
                console.log(`User with id ${profile.id} logged in. Address: ${addr.address}`);
            }
            cb(err, addr);
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

app.use(express.json())

if (process.env.NODE_ENV === 'development' || process.env.TESTING) {
    const corsOptions = {
        origin: function(origin, cb) {
            const whitelist = [
                'http://localhost:5000',
            ]

            // check if the request is from a origin in whitelist
            if (!origin || whitelist.indexOf(origin) !== -1) {
                cb(null, true)
            } else {
                cb(new Error('Not allowed by CORS'))
            }
        },
        credentials: true,
    }

    app.use(cors(corsOptions))
} else {
    app.use(cors())
}

app.use('/', express.static("build"));
app.use('/api/', router);

app.get('/auth/discord', passport.authenticate('discord'));
app.get('/auth/discord/callback', passport.authenticate('discord', {
    failureRedirect: '/'
}), function(req, res) {
    return res.redirect('/export') // Successful auth, redirect to export page
});

// Forward to index.html if a valid page
app.get('*', (req, res) => {
    const pages = [
        '/', '/export'
    ]
    if (pages.indexOf(req.path) === 1) {
        return res.sendFile(`/app/build/index.html`);
    }
});

// Catch all other routes return 404
app.all('*', (req, res) => {
    res.status(404).json({
        error: 'Not Found'
    });
});

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