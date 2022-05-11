print('Creating users...');
db = db.getSiblingDB("admin");
db.auth('root', 'rootpassword');

db = db.getSiblingDB('test');
// Create user for testing
db.createUser({
    user: "taotip", // taotip user
    pwd: "taotip",
    roles: [{
        role: "readWrite",
        db: "test"
    }]
});

db.createUser({
    user: "backend", // backend user
    pwd: "backend",
    roles: [{
        role: "read",
        db: "test"
    }]
});

db = db.getSiblingDB('prod');
db.createUser({
    user: "taotip", // taotip user
    pwd: "rootpassword",
    roles: [{
        role: "readWrite",
        db: "prod"
    }]
});

db.createUser({
    user: "backend", // backend user
    pwd: "prod_pass",
    roles: [{
        role: "read", // read-only
        db: "prod"
    }]
});
print('Done.');