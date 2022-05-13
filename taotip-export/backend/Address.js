import mongoose from "mongoose";

const addressSchema = new mongoose.Schema({
    user: 'String',
    address: 'String',
    mnemonic: 'Binary',
});

export default mongoose.model('Address', addressSchema);