print('Creating users...');
db = db.getSiblingDB("admin");
db.auth('root', 'rootpassword');

db = db.getSiblingDB('test');
db.createUser({
    user: "taotip",
    pwd: "taotip",
    roles: [{
        role: "readWrite",
        db: "test"
    }]
});

db = db.getSiblingDB('prod');
db.createUser({
    user: "taotip",
    pwd: "rootpassword",
    roles: [{
        role: "readWrite",
        db: "prod"
    }]
});
print('Done.');