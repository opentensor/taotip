db.createUser({
    user: "taotip",
    pwd: "<password of user>",
    roles: [{
        role: "readWrite",
        db: "test"
    }]
});

db.createUser({
    user: "taotip",
    pwd: "<password of user>",
    roles: [{
        role: "readWrite",
        db: "prod"
    }]
});