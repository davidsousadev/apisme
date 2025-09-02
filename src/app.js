import express from "express";
import usersRouter from "./routes/users.js";
import productsRouter from "./routes/products.js";

const app = express();
app.use(express.json());

// Rota raiz
app.get("/", (req, res) => {
  res.json({ "Documentação": "Acesse: https://apisme.vercel.app/docs" });
});

// Rotas
app.use("/users", usersRouter);
app.use("/products", productsRouter);

export default app;