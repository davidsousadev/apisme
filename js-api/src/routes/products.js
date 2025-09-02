import { Router } from "express";
const router = Router();

let products = [
  { id: 1, name: "Notebook" },
  { id: 2, name: "Mouse" }
];

// GET /products
router.get("/", (req, res) => {
  // #swagger.tags = ['Products']
  // #swagger.description = 'Retorna todos os produtos'
  // #swagger.responses[200] = { description: 'Lista de produtos', schema: [{id:1,name:'Notebook'}] }
  res.json(products);
});

// POST /products
router.post("/", (req, res) => {
  // #swagger.tags = ['Products']
  // #swagger.description = 'Adiciona um novo produto'
  // #swagger.parameters['obj'] = { in: 'body', description: 'Dados do produto', schema: { name: 'Teclado' } }
  const { name } = req.body;
  const newProduct = { id: products.length + 1, name };
  products.push(newProduct);
  res.status(201).json(newProduct);
});

// PUT /products
router.put("/", (req, res) => {
  // #swagger.tags = ['Products']
  // #swagger.description = 'Substitui todos os produtos'
  // #swagger.parameters['obj'] = { in: 'body', description: 'Nova lista de produtos', schema: [{id:1,name:'Notebook'}] }
  products = req.body;
  res.json(products);
});

// PATCH /products
router.patch("/", (req, res) => {
  // #swagger.tags = ['Products']
  // #swagger.description = 'Atualiza um produto específico'
  // #swagger.parameters['obj'] = { in: 'body', description: 'ID e novos dados do produto', schema: { id: 1, name: 'Mouse Atualizado' } }
  const { id, name } = req.body;
  products = products.map(p => p.id === id ? { ...p, name } : p);
  res.json(products.find(p => p.id === id));
});

// DELETE /products
router.delete("/", (req, res) => {
  // #swagger.tags = ['Products']
  // #swagger.description = 'Remove um produto pelo ID'
  // #swagger.parameters['obj'] = { in: 'body', description: 'ID do produto', schema: { id: 1 } }
  const { id } = req.body;
  products = products.filter(p => p.id !== id);
  res.json({ message: `Produto ${id} removido` });
});

// OPTIONS /products
router.options("/", (req, res) => {
  // #swagger.tags = ['Products']
  res.set("Allow", "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD").send();
});

// HEAD /products
router.head("/", (req, res) => {
  // #swagger.tags = ['Products']
  res.set("X-Total-Products", products.length).end();
});

export default router;