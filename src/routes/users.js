import { Router } from "express";
const router = Router();

router.get("/", (req, res) => {
  res.json([
    { id: 1, name: "David" },
    { id: 2, name: "Sousa" }
  ]);
});

router.post("/", (req, res) => {
  const user = req.body;
  user.id = Math.floor(Math.random() * 1000);
  res.status(201).json(user);
});

export default router;