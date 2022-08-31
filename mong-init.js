db.createUser({
    user: "taotip",
    pwd: "test_pass",
    roles: [{
        role: "readWrite",
        db: "test"
    }]
});

db.createUser({
    user: "taotip",
    pwd: "prod_pass",
    roles: [{
        role: "readWrite",
        db: "prod"
    }]
});