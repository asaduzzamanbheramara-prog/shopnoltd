const app = require("./src/app");

const PORT = process.env.PORT || 8001;


app.listen(PORT,()=>{

console.log(
`oauth-service running on port ${PORT}`
);

});
