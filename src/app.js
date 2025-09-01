import express from "express";
import expressOasGenerator from "express-oas-generator";
import usersRouter from "./routes/users.js";

const app = express();
app.use(express.json());

// Inicializa Swagger automático
expressOasGenerator.init(app, {
  docsPath: "/docs",
  exposeApiDocs: true
});

// Rotas
app.use("/users", usersRouter);

app.get("/", (req, res) => {
  res.json([{"Documentação": "Acesse: https://github.com/davidsousadev/apisme"}]);
});

export default app;