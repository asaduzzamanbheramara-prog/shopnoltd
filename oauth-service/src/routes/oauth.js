const express = require("express");
const jwt = require("jsonwebtoken");

const router = express.Router();

const secret =
process.env.JWT_SECRET || "shopnoltd-secret";


router.post("/token",(req,res)=>{

    const user = {
        id: 1,
        email: req.body.email || "user@shopnoltd.com"
    };


    const token = jwt.sign(
        user,
        secret,
        {
            expiresIn:"7d"
        }
    );


    res.json({
        token
    });

});


module.exports = router;
