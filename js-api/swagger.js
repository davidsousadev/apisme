import swaggerAutogen from "swagger-autogen";

const doc = {
  info: {
    title: "Apisme API",
    version: "1.0.0",
    description: "Documentação automática com Swagger Autogen",
  },
  host: "localhost:3000",
  schemes: ["http"],
  tags: [
    { name: "Users", description: "Operações relacionadas a usuários" },
    { name: "Products", description: "Operações relacionadas a produtos" },
  ],
};

const outputFile = "./swagger-output.json";
const endpointsFiles = [
  //"./src/routes/users.js",
  //"./src/routes/products.js"
  "./src/app.js"
];

swaggerAutogen()(outputFile, endpointsFiles, doc);