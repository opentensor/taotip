import 'dotenv/config'
import passport from 'passport'
import { Strategy as DiscordStrategy } from 'passport-discord'
import express from 'express'

scopes = ['identify', 'email', 'guilds', 'guilds.join'];