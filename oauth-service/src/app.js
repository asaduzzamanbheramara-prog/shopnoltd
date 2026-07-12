const express = require("express");
const cors = require("cors");

const oauthRoutes = require("./routes/oauth");

const app = express();

app.use(cors());
app.use(express.json());

app.get("/health",(req,res)=>{
    res.json({
        status:"ok",
        service:"oauth-service"
    });
});


app.use("/oauth",oauthRoutes);


module.exports = app;
