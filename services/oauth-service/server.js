const express = require("express");
const cors = require("cors");
const jwt = require("jsonwebtoken");

const app = express();

app.use(cors());
app.use(express.json());

const secret = process.env.JWT_SECRET || "shopnoltd-secret";


app.get("/health",(req,res)=>{
    res.json({
        status:"ok",
        service:"oauth-service"
    });
});


app.post("/oauth/token",(req,res)=>{

    const user={
        id:1,
        email:req.body.email || "user@shopnoltd.com"
    };


    const token=jwt.sign(
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


app.listen(8001,()=>{
 console.log("oauth running 8001");
});
