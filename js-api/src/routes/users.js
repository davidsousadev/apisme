import { Router } from "express";
const router = Router();

let users = [
  { id: 1, name: "Alice" },
  { id: 2, name: "Bob" },
];

// GET /users
router.get("/", (req, res) => {
  // #swagger.tags = ['Users']
  // #swagger.description = 'Retorna todos os usuários'
  // #swagger.responses[200] = { description: 'Lista de usuários', schema: [{id:1,name:'Alice'}] }
  res.json(users);
});

// POST /users
router.post("/", (req, res) => {
  // #swagger.tags = ['Users']
  // #swagger.description = 'Adiciona um novo usuário'
  // #swagger.parameters['obj'] = { in: 'body', description: 'Dados do usuário', schema: { name: 'Carlos' } }
  const { name } = req.body;
  const newUser = { id: users.length + 1, name };
  users.push(newUser);
  res.status(201).json(newUser);
});

// PUT /users
router.put("/", (req, res) => {
  // #swagger.tags = ['Users']
  // #swagger.description = 'Substitui todos os usuários'
  // #swagger.parameters['obj'] = { in: 'body', description: 'Nova lista de usuários', schema: [{id:1,name:'Alice'}] }
  users = req.body;
  res.json(users);
});

// PATCH /users
router.patch("/", (req, res) => {
  // #swagger.tags = ['Users']
  // #swagger.description = 'Atualiza um usuário específico'
  // #swagger.parameters['obj'] = { in: 'body', description: 'ID e novos dados do usuário', schema: { id: 1, name: 'Alice Atualizada' } }
  const { id, name } = req.body;
  users = users.map(user => user.id === id ? { ...user, name } : user);
  res.json(users.find(user => user.id === id));
});

// DELETE /users
router.delete("/", (req, res) => {
  // #swagger.tags = ['Users']
  // #swagger.description = 'Remove um usuário pelo ID'
  // #swagger.parameters['obj'] = { in: 'body', description: 'ID do usuário', schema: { id: 1 } }
  const { id } = req.body;
  users = users.filter(user => user.id !== id);
  res.json({ message: `Usuário ${id} removido` });
});

// OPTIONS /users
router.options("/", (req, res) => {
  // #swagger.tags = ['Users']
  res.set("Allow", "GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD").send();
});

// HEAD /users
router.head("/", (req, res) => {
  // #swagger.tags = ['Users']
  res.set("X-Total-Users", users.length).end();
});

export default router;